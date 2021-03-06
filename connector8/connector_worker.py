#!/usr/bin/env python
import sys
import logging
import time
import threading
from contextlib import closing
from psycopg2 import ProgrammingError

import openerp
from openerp.cli import server as servercli
import openerp.service.server as workers
from openerp.modules.registry import RegistryManager
from openerp.tools import config

_logger = logging.getLogger(__name__)

MAX_JOBS = 50


class Multicornnector(workers.PreforkServer):

    def __init__(self, app):
        super(Multicornnector, self).__init__(app)
        self.address = ('0.0.0.0', 0)
        self.population = config['workers'] or 1
        self.workers_connector = {}

    def process_spawn(self):
        while len(self.workers_connector) < self.population:
            self.worker_spawn(WorkerConnector, self.workers_connector)

    def worker_pop(self, pid):
        if pid in self.workers:
            _logger.debug("Worker (%s) unregistered", pid)
            try:
                self.workers_connector.pop(pid, None)
                u = self.workers.pop(pid)
                u.close()
            except OSError:
                return


class WorkerConnector(workers.Worker):
    """ HTTP Request workers """

    def __init__(self, multi):
        super(WorkerConnector, self).__init__(multi)
        self.db_index = 0

    def _work_database(self, cr):
        db_name = cr.dbname
        try:
            cr.execute("SELECT 1 FROM ir_module_module "
                       "WHERE name = %s "
                       "AND state = %s", ('connector', 'installed'),
                       log_exceptions=False)
        except ProgrammingError as err:
            if unicode(err).startswith(
                    'relation "ir_module_module" does not exist'):
                _logger.debug('Database %s is not an Odoo database,'
                              ' connector worker not started', db_name)
            else:
                raise
        else:
            if cr.fetchone():
                RegistryManager.check_registry_signaling(db_name)
                registry = openerp.pooler.get_pool(db_name)
                if registry:
                    queue_worker = registry['queue.worker']
                    queue_worker.assign_then_enqueue(cr,
                                                     openerp.SUPERUSER_ID,
                                                     max_jobs=MAX_JOBS)
                RegistryManager.signal_caches_change(db_name)

    def process_work(self):
        with openerp.api.Environment.manage():
            if config['db_name']:
                db_names = config['db_name'].split(',')
            else:
                db_names = openerp.service.db.exp_list(True)
            if len(db_names):
                self.db_index = (self.db_index + 1) % len(db_names)
                db_name = db_names[self.db_index]
                self.setproctitle(db_name)
                db = openerp.sql_db.db_connect(db_name)
                threading.current_thread().dbname = db_name
                with closing(db.cursor()) as cr:
                    self._work_database(cr)
            else:
                self.db_index = 0

    def sleep(self):
        # Really sleep once all the databases have been processed.
        if self.db_index == 0:
            interval = 15 + self.pid % self.multi.population  # chorus effect
            time.sleep(interval)

    def start(self):
        workers.Worker.start(self)


if __name__ == "__main__":
    args = sys.argv[1:]
    servercli.check_root_user()
    config.parse_config(args)

    servercli.check_postgres_user()
    openerp.netsvc.init_logger()
    servercli.report_configuration()

    openerp.multi_process = True
    openerp.worker_connector = True
    Multicornnector(openerp.service.wsgi_server.application).run([], False)
