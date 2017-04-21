# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os.path
import xml.etree.ElementTree as ET
from abc import ABCMeta, abstractmethod, abstractproperty
import Pyro4
from financeager.period import Period, TinyDbPeriod, XmlPeriod, CONFIG_DIR
from financeager.entries import BaseEntry


class Server(object):
    """Abstract class holding the database and communicated with via Pyro.

    The server creates a Period instance from the appropriate filepath in the
    config directory. It is typically launched at the initial `financeager`
    command line call and then runs in the background as a Pyro daemon.
    The `response` attribute can be used to access possible output data from
    querying commands (f.i. `print`). It holds a list of tinydb.database.Element
    objects (can be empty).
    """

    __metaclass__ = ABCMeta

    def __init__(self, period_name=None):
        self._running = True
        self._period_filepath = os.path.join(
                CONFIG_DIR, "{}.{}".format(
                    Period.DEFAULT_NAME if period_name is None else
                    period_name, self._file_suffix))
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        self._response = None
        self._command = None

    @abstractproperty
    def _file_suffix(self):
        pass

    @property
    def running(self):
        return self._running

    @Pyro4.expose
    @property
    def response(self):
        """Query and reset the server response. A list of strings is returned.
        This avoid serialization issues with Pyro4."""
        result = self._response
        self._response = None
        return result

    @abstractmethod
    def run(self, command, **kwargs):
        """The method of `Period` corresponding to the given `command` is
        looked up and called. All `kwargs` are passed on. The return value is
        stored in the `response` attribute.
        Calling `stop` causes the Pyro daemon request loop to terminate.
        """
        self._command = command
        if command == "stop":
            self._running = False
        else:
            command2method = {
                    "add": "add_entry",
                    "rm": "remove_entry",
                    "print": "print_entries"
                    }
            response = getattr(self._period, command2method[command])(**kwargs)
            self._response = response

@Pyro4.expose
class TinyDbServer(Server):
    """Server implementation holding a `TinyDbPeriod` database.

    All database handling is taken care of in the underlying `TinyDbPeriod`.
    Kwargs (f.i. storage) are passed to the TinyDbPeriod member.
    """

    NAME = "financeager_tinydb_server"

    def __init__(self, period_name=None, **kwargs):
        super(TinyDbServer, self).__init__(period_name)
        self._period = TinyDbPeriod(name=period_name, **kwargs)

    @property
    def _file_suffix(self):
        return "json"

    @staticmethod
    def name(period_name):
        return "financeager_tinydb_server.{}".format(period_name)

    def run(self, command, **kwargs):
        # graceful shutdown, invoke closing of files
        if command == "stop":
            self._period.close()
        super(TinyDbServer, self).run(command, **kwargs)
