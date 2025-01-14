# File: TscCommonLib.py ; This file is part of Twister.

# version: 3.024

# Copyright (C) 2012-2013 , Luxoft

# Authors:
#    Andrei Costachi <acostachi@luxoft.com>
#    Cristi Constantin <crconstantin@luxoft.com>
#    Daniel Cioata <dcioata@luxoft.com>
#    Mihail Tudoran <mtudoran@luxoft.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains common functions to communicate with the Central Engine.

The most important class is `TscCommonLib`, which is exposed both in Twister tests and libraries.

The exception classes are used to gracefully crash the Twister tests.
"""
from __future__ import print_function

import os
import copy
import time
import ast
import inspect
import binascii
import platform
import marshal
import rpyc
from rpyc import BgServingThread
# This will work, because TWISTER_PATH is appended to sys.path.
try:
    from ce_libs import PROXY_ADDR, USER, EP, SUT
except Exception:
    raise Exception('CommonLib must run from Twister!\n')

TWISTER_PATH = os.getenv('TWISTER_PATH')
if not TWISTER_PATH:
    raise Exception('$TWISTER_PATH environment variable is not set!\n')

__all__ = ['TscCommonLib', 'ExceptionTestFail', 'ExceptionTestAbort', 'ExceptionTestTimeout', 'ExceptionTestSkip']

#

class TwisterException(Warning):
    """
    Base custom exception.
    """
    def __init__(self, value=''):
        self.value = value
    def __str__(self):
        return str(self.value)


class ExceptionTestFail(TwisterException):
    """
    Custom exception, caught by the EP.
    """
    pass

class ExceptionTestAbort(TwisterException):
    """
    Custom exception, caught by the EP.
    """
    pass

class ExceptionTestTimeout(TwisterException):
    """
    Custom exception, caught by the EP.
    """
    pass

class ExceptionTestSkip(TwisterException):
    """
    Custom exception, caught by the EP.
    """
    pass

#

class TscCommonLib(object):
    """
    Base library for Twister tests and libraries.

    All functions are exposed automatically.
    """

    platform_sys = platform.system().lower()
    """ Current platform. (ex: Windows, Linux) """

    __ce_proxy = None
    """ Pointer to Central Engine via RPyc. """

    proxy_path = PROXY_ADDR
    """ The Central Engine RPyc address. """

    userName = USER
    """ The username running this test, or libary. """

    epName = EP
    """ The EP running this test, or libary. """

    global_vars = {}
    """ All global variables, shared between tests and libaries. """

    interact_data = None
    _SUITE_ID = 0
    _FILE_ID = 0


    def __init__(self):
        """
        Some initialization code.
        """
        self._reload_libs()


    def _reload_libs(self):
        """ Internal function. Reload libraries. """
        from common import iniparser
        ce_path = '{}/.twister_cache/{}/ce_libs/ce_libs.py'.format(TWISTER_PATH, self.epName)
        cfg = iniparser.ConfigObj(ce_path)
        for n, v in cfg.iteritems():
            setattr(self, '_' + n, v)
        del cfg


    @property
    def sutName(self):
        """ Returns current SUT name. """
        self._reload_libs()
        name = self.ce_proxy.get_suite_variable(self.epName, self._SUITE_ID, 'sut')
        return name


    @property
    def SUT(self):
        """ Returns current SUT name; same as sutName. """
        self._reload_libs()
        name = self.ce_proxy.get_suite_variable(self.epName, self._SUITE_ID, 'sut')
        return name


    @property
    def SUITE_ID(self):
        """ Returns current suite ID. """
        self._reload_libs()
        return self._SUITE_ID


    @property
    def FILE_ID(self):
        """ Returns current file ID. """
        self._reload_libs()
        return self._FILE_ID


    @property
    def SUITE_NAME(self):
        """ Returns current suite name. """
        self._reload_libs()
        name = self.ce_proxy.get_suite_variable(self.epName, self._SUITE_ID, 'name')
        return name


    @property
    def FILE_NAME(self):
        """ Returns current file name. """
        self._reload_libs()
        name = self.ce_proxy.get_file_variable(self.epName, self._FILE_ID, 'file')
        if name:
            name = os.path.split(name)[1]
        return name


    @classmethod
    def _ce_proxy(cls):
        """
        Dinamically connect to the Central Engine.
        This is a class method.
        """
        stack = inspect.stack()
        # The upper stack is either the EP, or the library that derives this
        stack_fpath = stack[1][1]
        stack_fname = os.path.split(stack_fpath)[1]
        proxy = None

        # If the upper stack is not ExecutionProcess, the library is derived
        if stack_fname != 'ExecutionProcess.py':
            # The EP stack is always the last
            ep_code = stack[-1][0]
            # It's impossible to access the globals from the EP any other way
            p = ep_code.f_globals.get('ceProxy')
            if p:
                return p.root
        del stack, stack_fpath

        # Try to reuse the old connection
        try:
            cls.__ce_proxy.echo('ping')
            return cls.__ce_proxy
        except Exception:
            pass

        # RPyc config
        config = {
            'allow_pickle': True,
            'allow_getattr': True,
            'allow_setattr': True,
            'allow_delattr': True,
            'allow_all_attrs': True,
            }

        ce_ip, ce_port = cls.proxy_path.split(':')

        # If the old connection is broken, connect to the RPyc server
        try:
            # Transform XML-RPC port into RPyc Port; RPyc port = XML-RPC port + 10 !
            ce_port = int(ce_port) + 10
            proxy = rpyc.connect(ce_ip, ce_port, config=config)
            proxy.root.hello('lib::{}'.format(cls.epName))
        except Exception:
            print('*ERROR* Cannot connect to CE path `{}`! Exiting!'.format(cls.proxy_path))
            raise Exception('Cannot connect to CE')

        # Authenticate on RPyc server
        try:
            proxy.root.login(cls.userName, 'EP')
        except Exception:
            print('*ERROR* Cannot authenticate on CE path `{}`! Exiting!'.format(cls.proxy_path))
            raise Exception('Cannot authenticate on CE')

        # Launch bg server
        try:
            BgServingThread(proxy)
            cls.__ce_proxy = proxy.root
            return cls.__ce_proxy
        except Exception:
            print('*ERROR* Cannot launch Bg serving thread! Exiting!')
            raise Exception('Cannot launch Bg thread')


    @property
    def ce_proxy(self):
        """
        Pointer to the Central Engine RPyc connection.
        """
        return self._ce_proxy()


    @staticmethod
    def test_fail(reason=''):
        """
        Gracefully crash test with status `Fail`.
        """
        raise ExceptionTestFail(reason)


    @staticmethod
    def test_abort(reason=''):
        """
        Gracefully crash test with status `Abort`.
        """
        raise ExceptionTestAbort(reason)


    @staticmethod
    def test_timeout(reason=''):
        """
        Gracefully crash test with status `Timeout`.
        """
        raise ExceptionTestTimeout(reason)


    @staticmethod
    def test_skip(reason=''):
        """
        Gracefully crash test with status `Skip`.
        """
        raise ExceptionTestSkip(reason)


    def interact(self, type, msg, timeout=0, options={}):
        """
        This function should be called only from a test!
        It gives to user the opportunity to interact with tests.
        Params:
        type: type of the interaction: confirmation window, input window, continue/cancel window
        msg: the message that will be printed in the window
        return: True/False or a string
        """
        self.interact_data = None
        print('\n>> Waiting for user interaction >>')
        id = binascii.hexlify(os.urandom(4))
        self.ce_proxy.interact(id, self.epName, type, msg, timeout, options)
        time.sleep(1)
        counter = 0.0
        while self.interact_data == None:
            time.sleep(0.5)
            if timeout > 0:
                counter += 0.5
                if counter > timeout:
                    break
        counter = 0.0
        reason = 'User action'
        if type == 'decide' and self.interact_data in [None, 'false']:
            # abort test!
            if self.interact_data == None:
                reason = 'Decide timeout expired!'
            else:
                reason = 'Test aborted by user!'
            self.ce_proxy.set_file_status(self.epName, self._FILE_ID, 5, timeout)
            self.ce_proxy.set_ep_status(self.epName, 2)
            print('\n>> Test aborted by user! >>')
            self.ce_proxy.remove_interact(id, self.epName, type, msg, timeout, options, reason)
            raise ExceptionTestAbort(reason)

        if self.interact_data == None:
            reason = 'Timeout expired'
            print('Interaction timeout expired!')
            if type == 'msg':
                self.interact_data = True
            elif type == 'options' and options:
                self.interact_data = options['default']

        self.ce_proxy.set_ep_status(self.epName, 2)
        self.ce_proxy.remove_interact(id, self.epName, type, msg, timeout, options, reason)
        print('\n>> Interaction response: {} >>'.format(self.interact_data))
        return self.interact_data


    def log_msg(self, log_type, log_message):
        """
        Send a message in a specific log, on Central Engine.
        """
        if not log_message:
            log_message = ''
        else:
            log_message = str(log_message)
        self.ce_proxy.log_message(log_type, log_message)


    @classmethod
    def get_global(cls, var):
        """
        Function to get variables saved from Test files.
        The same data must be used, both in Testcase and derived Libraries.
        """
        if var in cls.global_vars:
            return cls.global_vars[var]
        # Else...
        ce = cls._ce_proxy()
        return ce.get_global_variable(var)


    @classmethod
    def set_global(cls, var, value):
        """
        Function to keep variables sent from Test files.
        The same data must be used, both in Testcase and derived Libraries.
        """
        try:
            marshal.dumps(value)
            ce = cls._ce_proxy()
            return ce.set_global_variable(var, value)
        except Exception:
            cls.global_vars[var] = value
            return True


    def get_config(self, cfg_path, var_path=''):
        """
        Get data from a config, using the full path to the config file and
        the full path to a config variable in that file.
        """
        return self.ce_proxy.get_config(cfg_path, var_path)


    def set_binding(self, config_name, component, sut):
        """
        Method to set a config->SUT binding
        """
        return self.ce_proxy.set_binding(config_name, component, sut)


    def del_binding(self, config_name, component):
        """
        Method that deletes a binding from the list of config->SUT bindings
        """
        return self.ce_proxy.del_binding(config_name, component)


    def get_binding(self, cfg_root):
        """
        Function to get a config -> SUT binding.
        """
        bindings = self.ce_proxy.get_user_variable('bindings') or {}
        return bindings.get(cfg_root)

    def get_bind_id(self, component_name, test_config='default_binding'):
        """
        Function to get a config -> SUT binding ID.
        Shortcut function.
        """
        bindings = self.ce_proxy.get_user_variable('bindings') or {}
        # Fix cfg root maybe ?
        if not test_config:
            test_config = 'default_binding'
        config_data = bindings.get(test_config, {})
        # If the component cannot be found in the requested config, search in default config
        if test_config != 'default_binding' and (component_name not in config_data):
            config_data = bindings.get('default_binding', {})
        return config_data.get(component_name, False)


    def get_bind_name(self, component_name, test_config='default_binding'):
        """
        Function to get a cfg -> SUT binding name.
        Shortcut function.
        """
        sid = self.get_bind_id(component_name, test_config)
        if not sid:
            return False
        sut = self.get_sut(sid)
        if not sut:
            sut = {}
        return sut.get('path', False)


    def get_iter_value(self, iter_name, cfg_name=None):
        """
        Find iteration value, for a specific iterator name.
        `iter_name` is the name of the iterator to search.
        Returns The iterator value.
        """
        iterNr = self.ce_proxy.get_file_variable(self.epName, self._FILE_ID, 'iterationNr')

        found = []
        if cfg_name is not None:
            # if the test configuration name is valid, find it in iterNr
            cfg_iters = [cfg_item.strip() for cfg_item in iterNr.strip().\
            split(',') if cfg_name in cfg_item.split('#')[0]]
            # now we have a list with iterators declared in cfg_name file
            # search the specified one
            found = [iter_val.split('=')[-1] for iter_val in cfg_iters \
            if '#{}='.format(iter_name) in iter_val]
        else:
            # no test configuration name provided, search for all iterators
            # that match iter_name
            found = [i.split('=')[-1] for i in iterNr.split(',') \
            if '#{}='.format(iter_name) in i]

        if not found:
            return ''
        return found[0]

    def get_iter_comp(self, iter_name, cfg_name=None):
        """
        Find component name that is parent of specific iterator name.
        `iter_name` is the name of the iterator to search.
        Returns the component name 
        """
        iterNr = self.ce_proxy.get_file_variable(self.epName, self._FILE_ID, 'iterationNr')

        found = []
        if cfg_name is not None:
            # if the test configuration name is valid, find it in iterNr
            cfg_iters = [cfg_item.strip() for cfg_item in iterNr.strip().\
            split(',') if cfg_name in cfg_item.split('#')[0]]
            # now we have a list with iterators declared in cfg_name file
            # search the specified one
            found = [iter_val.split('#')[1] for iter_val in cfg_iters \
            if '#{}='.format(iter_name) in iter_val]
        else:
            # no test configuration name provided, search for all iterators
            # that match iter_name
            found = [i.split('#')[1] for i in iterNr.split(',') \
            if '#{}='.format(iter_name) in i]

        if not found:
            return ''
        return found[0]


    def count_project_files(self):
        """
        Returns the number of files inside the current project.
        """
        data = self.ce_proxy.get_ep_variable(self.epName, 'suites')
        SuitesManager = copy.deepcopy(data)
        files = SuitesManager.get_files(recursive=True)
        return len(files)


    def current_file_index(self):
        """
        Returns the index of this file in the project.
        If the file ID is not found, the count will fail.
        """
        data = self.ce_proxy.get_ep_variable(self.epName, 'suites')
        SuitesManager = copy.deepcopy(data)
        files = SuitesManager.get_files(recursive=True)
        try:
            return files.index(self.FILE_ID)
        except Exception:
            return -1


    def count_suite_files(self):
        """
        Returns the number of files inside a suite ID.
        If the suite ID is not found, the count will fail.
        """
        data = self.ce_proxy.get_suite_variable(self.epName, self.SUITE_ID, 'children')
        SuitesManager = copy.deepcopy(data)
        files = SuitesManager.keys() # First level of files, depth=1
        return len(files)


    def current_fsuite_index(self):
        """
        Returns the index of this file, inside this suite.
        If the suite ID and file ID are not found, the count will fail.
        """
        data = self.ce_proxy.get_suite_variable(self.epName, self.SUITE_ID, 'children')
        SuitesManager = copy.deepcopy(data)
        files = SuitesManager.keys() # First level of files, depth=1
        try:
            return files.index(self.FILE_ID)
        except Exception:
            return -1


    def py_exec(self, code_string):
        """
        Expose Python functions and class instances in TCL.
        """
        if not isinstance(code_string, str):
            print('py_exec: Error, the code must be a string `{}`!'.format(code_string))
            return False

        try:
            ret = eval(code_string, self.global_vars, self.global_vars)
        except Exception, e:
            print('py_exec: Error execution code `{}`! Exception `{}`!'.format(code_string, e))
            ret = False

        return ret


    def _encode_unicode(self, input):
        """
        Encode data to UTF-8.
        """
        if isinstance(input, dict):
            return {self._encode_unicode(key): self._encode_unicode(value) for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [self._encode_unicode(elem) for elem in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input


    def get_tb(self, query, dtype=unicode):
        """
        Get TB content.
        """
        try:
            data = self.ce_proxy.get_tb(query)
            if dtype == str:
                return self._encode_unicode(data)
            else:
                return data
        except Exception as e:
            print('Error on get Resource! `{}`!'.format(e))
            return None


    def get_resource(self, query, dtype=unicode):
        """
        Get TB content. Alias function for `get_tb`.
        """
        return self.get_tb(query, dtype)


    def create_new_tb(self, name, parent='/', props={}):
        """
        Update a TB.
        """
        try:
            return self.ce_proxy.create_new_tb(name, parent, props)
        except Exception as e:
            print('Error on create Resource! `{}`!'.format(e))
            return None


    def create_component_tb(self, name, parent='/', props={}):
        """
        Update a TB.
        """
        try:
            return self.ce_proxy.create_component_tb(name, parent, props)
        except Exception as e:
            print('Error on create Resource! `{}`!'.format(e))
            return None


    def update_meta_tb(self, name, parent='/', props={}):
        """
        Update a TB.
        """
        try:
            return self.ce_proxy.update_meta_tb(name, parent, props)
        except Exception as e:
            print('Error on update Resource! `{}`!'.format(e))
            return None


    def set_tb(self, name, parent='/', props={}):
        """
        Update a TB. High level function.
        """
        if isinstance(props, str) or isinstance(props, unicode):
            try:
                props = ast.literal_eval(props)
            except Exception:
                pass
        try:
            return self.ce_proxy.set_tb(name, parent, props)
        except Exception as e:
            print('Error on set Resource! `{}`!'.format(e))
            return None


    def set_resource(self, name, parent='/', props={}):
        """
        Update a TB. Alias function for `set_tb`.
        """
        return self.set_tb(name, parent, props)


    def rename_tb(self, res_query, new_name):
        """
        Rename a TB.
        """
        try:
            return self.ce_proxy.rename_tb(res_query, new_name)
        except Exception as e:
            print('Error on rename Resource! `{}`!'.format(e))
            return None


    def rename_resource(self, res_query, new_name):
        """
        Rename a TB. Alias function for `rename_tb`.
        """
        return self.rename_tb(res_query, new_name)


    def delete_tb(self, query):
        """
        Delete a TB.
        """
        try:
            return self.ce_proxy.delete_tb(query)
        except Exception as e:
            print('Error on delete Resource! `{}`!'.format(e))
            return None


    def delete_resource(self, query):
        """
        Delete a TB. Alias function for `delete_tb`.
        """
        return self.delete_tb(query)


    def get_sut(self, query, follow_links=False, dtype=unicode):
        """
        Get SUT content.
        query : id/path of sut
        """
        try:
            data = self.ce_proxy.get_sut(query, follow_links)
            if dtype == str:
                return self._encode_unicode(data)
            else:
                return data
        except Exception as e:
            print('Error on get SUT! `{}`!'.format(e))
            return None


    def get_info_sut(self, query):
        """
        Get SUT info.
        """
        try:
            return self.ce_proxy.get_info_sut(query)
        except Exception as e:
            print('Error on get info SUT! `{}`!'.format(e))
            return None


    def create_new_sut(self, name, parent='/', props={}):
        """
        Update a SUT.
        """
        try:
            return self.ce_proxy.create_new_sut(name, parent, props)
        except Exception as e:
            print('Error on create SUT! `{}`!'.format(e))
            return None


    def create_component_sut(self, name, parent='/', props={}):
        """
        Update a SUT.
        """
        try:
            return self.ce_proxy.create_component_sut(name, parent, props)
        except Exception as e:
            print('Error on create SUT! `{}`!'.format(e))
            return None


    def update_meta_sut(self, name, parent='/', props={}):
        """
        Update a SUT.
        """
        try:
            return self.ce_proxy.update_meta_sut(name, parent, props)
        except Exception as e:
            print('Error on update SUT! `{}`!'.format(e))
            return None


    def set_sut(self, name, parent='/', props={}):
        """
        Update a SUT.
        """
        try:
            return self.ce_proxy.set_sut(name, parent, props)
        except Exception as e:
            print('Error on set SUT! `{}`!'.format(e))
            return None


    def rename_sut(self, res_query, new_name):
        """
        Rename a SUT.
        """
        try:
            return self.ce_proxy.rename_sut(res_query, new_name)
        except Exception as e:
            print('Error on rename SUT! `{}`!'.format(e))
            return None


    def delete_sut(self, query):
        """
        Delete a SUT.
        """
        try:
            return self.ce_proxy.delete_sut(query)
        except Exception as e:
            print('Error on delete SUT! `{}`!'.format(e))
            return None


    def delete_component_sut(self, query):
        """
        Delete a SUT component.
        """
        try:
            return self.ce_proxy.delete_component_sut(query)
        except Exception as e:
            print('Error on delete SUT component! `{}`!'.format(e))
            return None


    def reserve_tb(self, query):
        """
        Reserve a resource. You can then edit the resource.
        """
        try:
            return self.ce_proxy.reserve_tb(query)
        except Exception as e:
            print('Error on reserve resource! `{}`!'.format(e))
            return None


    def save_reserved_tb(self, query):
        """
        Save changes. Don't release.
        """
        try:
            return self.ce_proxy.save_reserved_tb(query)
        except Exception as e:
            print('Error on save resource! `{}`!'.format(e))
            return None


    def save_release_reserved_tb(self, query):
        """
        Save changes. Release the resource.
        """
        try:
            return self.ce_proxy.save_release_reserved_tb(query)
        except Exception as e:
            print('Error on save & release resource! `{}`!'.format(e))
            return None


    def discard_release_reserved_tb(self, query):
        """
        Drop changes. Release the resource.
        """
        try:
            return self.ce_proxy.discard_release_reserved_tb(query)
        except Exception as e:
            print('Error on discard & release resource! `{}`!'.format(e))
            return None


    def reserve_sut(self, query):
        """
        Reserve a SUT. You can then edit the SUT.
        """
        try:
            return self.ce_proxy.reserve_sut(query)
        except Exception as e:
            print('Error on reserve SUT! `{}`!'.format(e))
            return None


    def save_reserved_sut(self, query):
        """
        Save changes. Don't release.
        """
        try:
            return self.ce_proxy.save_reserved_sut(query)
        except Exception as e:
            print('Error on save SUT! `{}`!'.format(e))
            return None


    def save_release_reserved_sut(self, query):
        """
        Save changes. Release the SUT.
        """
        try:
            return self.ce_proxy.save_release_reserved_sut(query)
        except Exception as e:
            print('Error on save & release SUT! `{}`!'.format(e))
            return None


    def discard_release_reserved_sut(self, query):
        """
        Drop changes. Release the SUT.
        """
        try:
            return self.ce_proxy.discard_release_reserved_sut(query)
        except Exception as e:
            print('Error on discard & release SUT! `{}`!'.format(e))
            return None


    def is_tb_reserved(self, query):
        """
        Yes or No.
        """
        try:
            result = self.ce_proxy.is_tb_reserved(query)
            if not result or result == 'false':
                return False
            else:
                return True
        except Exception as e:
            print('Error on discard & release SUT! `{}`!'.format(e))
            return None


    def get_tb_user(self, query):
        """
        User name.
        """
        try:
            result = self.ce_proxy.is_tb_reserved(query)
            if not result or result == 'false':
                return False
            else:
                return result
        except Exception as e:
            print('Error on discard & release SUT! `{}`!'.format(e))
            return None


    def is_sut_reserved(self, query):
        """
        Yes or No.
        """
        try:
            result = self.ce_proxy.is_sut_reserved(query)
            if not result or result == 'false':
                return False
            else:
                return True
        except Exception as e:
            print('Error on discard & release SUT! `{}`!'.format(e))
            return None


    def get_sut_user(self, query):
        """
        User name.
        """
        try:
            result = self.ce_proxy.is_sut_reserved(query)
            if not result or result == 'false':
                return False
            else:
                return result
        except Exception as e:
            print('Error on discard & release SUT! `{}`!'.format(e))
            return None


# Eof()
