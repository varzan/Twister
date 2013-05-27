
# File: TestCaseRunner.py ; This file is part of Twister.

# version: 2.002

# Copyright (C) 2012-2013 , Luxoft

# Authors:
#    Adrian Toader <adtoader@luxoft.com>
#    Andrei Costachi <acostachi@luxoft.com>
#    Andrei Toma <atoma@luxoft.com>
#    Cristi Constantin <crconstantin@luxoft.com>
#    Daniel Cioata <dcioata@luxoft.com>

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
Test Case Runner has the following roles:
 - Connects to CE to receive the libs and files that must be executed on this station.
 - Takes the statuses from last run to see if the last run was killed by timeout,
    and if it was, it must skip the files that were already executed.
 - It reads the START/ STOP/ PAUSE/ RESUME status and if it's PAUSE, it waits for RESUME.
 - It checks for current file dependencies, if there are any, it waits for the dependency to be executed.
 - It skips the files that have status SKIP.
 - It downloads the files that must be executed, directly from CE.
 - It executes test files, counting the execution time. If the file takes too long, the Runner exits
    and will be restarted by EP. If the execution is successful, it sends the status and the time to CE.
 - The files that must be executed can be in many formats, ex: Python, Perl, TCL, the Runner detects
    them by extension.

This script should NOT be run manually!
"""

import os
import sys
import shutil
import time
import pickle
import marshal
import xmlrpclib
import tarfile
import traceback

from collections import OrderedDict
from threading import Timer

TWISTER_PATH = os.getenv('TWISTER_PATH')
if not TWISTER_PATH:
    print('TWISTER_PATH environment variable is not set! Exiting!')
    exit(1)
sys.path.append(TWISTER_PATH)

from common.constants import *
import TestCaseRunnerClasses
from TestCaseRunnerClasses import *

#

def Suicide(proxy, sig=9, msg=None, file_id=None, status_f=None, timer_f=None):
    """
    Function Suicide is used to kill current process.
    """
    if msg:
        proxy.echo(':: {0} {1}...'.format(self.epName, msg.strip()))
    if (file_id is not None) and (status_f is not None) and (timer_f is not None):
        self.proxySetTestStatus(file_id, status_f, timer_f)
    pid = os.getpid()
    print('TC debug: Killing PID `{0}`.'.format(pid))
    # Kill PID
    try: os.kill(pid, sig)
    except: os.kill(pid, 9)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


class TwisterRunner:

    def __init__(self, userName, epName):

        global TWISTER_PATH

        self.userName = userName
        self.epName   = epName
        self.tbName   = None
        # Central Engine XML-RPC connection
        self.proxy    = None
        # For storing temporary variables
        self.global_vars   = {}
        # All known runners
        self.runners = {
            'tcl': None,
            'python': None,
            'perl': None,
            'java': None,
        }

        self.EP_CACHE = TWISTER_PATH + '/.twister_cache/' + epName

        self.loadConfig()

        # Connect to RPC server
        try:
            self.proxy = xmlrpclib.ServerProxy(self.CONFIG['PROXY'])
            self.proxy.echo('ping')
        except:
            print('TC error: Cannot connect to CE path `{}`! Exiting!'.format(self.CONFIG['PROXY']))
            exit(1)

        # Save all libraries from CE
        self.saveLibraries()
        # After download, inject libraries path for the current EP
        sys.path.append(self.EP_CACHE)

        try:
            import ce_libs
        except:
            print('TC error: Cannot import the shared libraries!')
            exit(1)


    def loadConfig(self):
        """
        Load the config file written by the EP.
        """
        if not os.path.isdir(self.EP_CACHE):
            print('TC error: Internal error! Cannot find `{}` cache folder! Exiting!'.format(epName))
            exit(1)

        try:
            f = open(self.EP_CACHE + '/data.pkl', 'rb')
            self.CONFIG = pickle.load(f)
            f.close() ; del f
        except:
            print('TC error: Internal error! Cannot read config file `{}`! Exiting!'.format(self.EP_CACHE))
            exit(1)


    def saveLibraries(self, libs_list=''):
        """
        Downloads all libraries from Central Engine.
        """

        global TWISTER_PATH

        libs_path = '{}/.twister_cache/{}/ce_libs'.format(TWISTER_PATH, self.epName)
        reset_libs = False

        if not libs_list:
            libs_list = self.proxy.getLibrariesList(userName)
            reset_libs = True
        else:
            libs_list = [lib.strip() for lib in libs_list.split(';')]

        if reset_libs:
            # Remove libs path only if saving libraries for all project
            shutil.rmtree(libs_path, ignore_errors=True)
            # Create the path, after removal
            try: os.makedirs(libs_path)
            except: pass

        all_libs = [] # Normal python files or folders
        zip_libs = [] # Zip libraries

        # If Reseting libs, open and destroy
        if reset_libs:
            __init = open(libs_path + os.sep + '__init__.py', 'w')
            __init.write('\nimport os, sys\n')
            __init.write('\nPROXY = "{}"\n'.format(self.CONFIG['PROXY']))
        # If not Reseting, just append
        else:
            __init = open(libs_path + os.sep + '__init__.py', 'a')

        for lib in libs_list:
            if not lib:
                continue
            if lib.endswith('.zip'):
                zip_libs.append(lib)
            else:
                all_libs.append(lib)

        if reset_libs:
            __init.write('\nall = ["%s"]\n\n' % ('", "'.join([os.path.splitext(lib)[0] for lib in all_libs])))
        else:
            __init.write('\nall += ["%s"]\n\n' % ('", "'.join([os.path.splitext(lib)[0] for lib in all_libs])))

        for lib_file in zip_libs:
            lib_data = self.proxy.downloadLibrary(lib_file)
            time.sleep(0.1) # Must take it slow
            if not lib_data:
                print('ZIP library `{0}` does not exist!'.format(lib_file))
                continue

            print('Downloading Zip library `{0}` ...'.format(lib_file))

            # Write ZIP imports.
            __init.write('\nsys.path.append(os.path.split(__file__)[0] + "/{}")\n\n'.format(lib_file))
            lib_pth = libs_path + os.sep + lib_file

            f = open(lib_pth, 'wb')
            f.write(lib_data.data)
            f.close() ; del f

        for lib_file in all_libs:
            lib_data = self.proxy.downloadLibrary(lib_file)
            time.sleep(0.1) # Must take it slow
            if not lib_data:
                print('Library `{0}` does not exist!'.format(lib_file))
                continue

            print('Downloading library `{0}` ...'.format(lib_file))

            ext = os.path.splitext(lib_file)
            # Write normal imports.
            __init.write('import %s\n' % ext[0])
            __init.write('from %s import *\n\n' % ext[0])
            lib_pth = libs_path + os.sep + lib_file

            f = open(lib_pth, 'wb')
            f.write(lib_data.data)
            f.close() ; del f

            # If the file doesn't have an ext, it's a TGZ library and must be extracted
            if not ext[1]:
                # Rename the TGZ
                tgz = lib_pth + '.tgz'
                os.rename(lib_pth, tgz)
                # Need to wait more on slow machines
                for i in range(20):
                    try: tarfile.open(tgz, 'r:gz')
                    except: time.sleep(0.5)
                with tarfile.open(tgz, 'r:gz') as binary:
                    os.chdir(libs_path)
                    binary.extractall()

        __init.close()

# # #

    def proxySetTestStatus(self, file_id, status, time_t):
        """
        Shortcut function for setting Test status.
        """
        self.proxy.setFileStatus(self.userName, self.epName, file_id, status, time_t)


    def logMsg(self, logType, logMessage):
        """
        Shortcut function for sending a message in a log to Central Engine.
        """
        self.proxy.logMessage(self.userName, logType, logMessage)


    def getGlobal(self, var):
        """
        Function to get variables saved from Test files.
        """
        if var in self.global_vars:
            return self.global_vars[var]
        # Else...
        return self.proxy.getGlobalVariable(self.userName, var)


    def setGlobal(self, var, value):
        """
        Function to keep variables sent from Test files.
        """
        try:
            marshal.dumps(value)
            return self.proxy.setGlobalVariable(self.userName, var, value)
        except:
            self.global_vars[var] = value
            return True


    def py_exec(self, code_string):
        """
        Exposed Python function and class instances for TCL.
        """
        if not isinstance(code_string, str):
            print('py_exec: Error, the code must be a string `{}`!'.format(code_string))
            return False

        try: ret = eval(code_string, self.global_vars, self.global_vars)
        except Exception, e:
            print('py_exec: Error execution code `{}`! Exception `{}`!'.format(code_string, e))
            ret = False

        return ret

# # #

    def Rindex(self, l, val):
        """ Find element in list from the end """
        for i, j in enumerate(reversed(l)):
            if j == val: return len(l) - i - 1
        return -1


    def run(self):
        """
        Cycle in all files, run each file, in order.
        """

        if self.CONFIG['STATUS'] == 'running':
            print('TC debug: Connected Central Engine, running tests!')
        else:
            print('TC debug: EP name `{}` is NOT running! Exiting!'.format(self.epName))
            exit(1)

        # Download the Suites Manager from Central Engine!
        # This is the initial structure, created from the Project.XML file.
        suites_pickle = self.proxy.getEpVariable(self.userName, self.epName, 'suites', True)
        SuitesManager = pickle.loads(suites_pickle)
        del suites_pickle


        # Get the `exit on test Fail` value
        exit_on_test_fail = self.proxy.getUserVariable(self.userName, 'exit_on_test_fail')
        # Get tests delay
        tc_delay = self.proxy.getUserVariable(self.userName, 'tc_delay')

        # Used by all files
        suite_id    = None
        suite_name  = None # Suite name string. This varies for each file.
        suite_files = None # All files from current suite.
        abort_suite = False # Abort suite X, when prerequisite file fails.


        for id, node in SuitesManager.iterNodes():

            # Starting a new suite or sub-suite ...
            # Some files don't belong to this suite, they might belong to the parent of this suite,
            # so each file must update the suite ID!
            if node['type'] == 'suite':

                if not node['children']:
                    print('TC warning: Nothing to do in suite `{}`!\n'.format(suite_str))
                    continue

                suite_id   = id
                suite_name = node['name']
                suite_str  = suite_id +' - '+ suite_name

                # The Test Bed name. Common for all files in this EP.
                self.tbName = node['tb']

                print('\n===== ===== ===== ===== =====')
                print(' Starting suite `{}`'.format(suite_str))
                print('===== ===== ===== ===== =====\n')

                # Get list of libraries for current suite
                libList = node['libraries']
                if libList:
                    saveLibraries(libList)
                    print('')

                # The end of the suite
                continue


            # Files section
            file_id  = id
            suite_id = node['suite']

            # All files from current suite, recursive, unlimited depth
            suite_files = SuitesManager.getFiles(suite_id)
            try:
                file_index  = suite_files.index(file_id)
            except:
                print('Invalid file list for suite `{}`! This is a serious error!'.format(suite_id))
                file_index = -1
            status  = node.get('status', STATUS_INVALID)

            # The name of the file
            filename = node['file']
            # Is this file Prerequisite?
            prerequisite = node.get('Prerequisite')
            # Test-case dependency, if any
            dependancy = node.get('dependancy')
            # Is this test file optional?
            optional_test = node.get('Optional')
            # Get args
            args = node.get('param')
            if args:
                args = [p for p in args.split(',') if p]
            else:
                args = []

            print('<<< START filename: `{}:{}` >>>\n'.format(file_id, filename))


            # If the prerequisite file failed, abort the current suite and all sub-suites!
            # Strategy: list all children from the aborted suite. If the current file is a child
            # of the aborted suite, this file must be aborted too!
            # Abort_suite flag is set by the first prerequisite file from a suite.
            if abort_suite:
                aborted_ids = SuitesManager.getFiles(abort_suite)
                if aborted_ids and file_id in aborted_ids:
                    print('TC debug: Abort file `{}` because of prerequisite file!\n\n'.format(filename))
                    self.proxySetTestStatus(file_id, STATUS_ABORTED, 0.0) # File status ABORTED
                    print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                    continue


            # Reload the config file written by EP
            self.loadConfig()

            # When a test file is about to be executed and STOP is received, send status ABORTED
            if self.CONFIG['STATUS'] == 'stopped':
                Suicide('ABORTED: Status STOP, while running!', file_id, STATUS_ABORTED, 0.0)

            # On pause, freeze cycle and wait for Resume or Stop
            elif self.CONFIG['STATUS'] == 'paused':
                self.proxy.echo(':: {} is paused!... Must RESUME to continue, or STOP to exit test suite...'.format(self.epName))
                vPauseMsg = False
                while 1:
                    # Print pause message
                    if not vPauseMsg:
                        print('Runner: Execution paused. Waiting for RESUME signal.\n')
                        vPauseMsg = True
                    time.sleep(3)
                    # Reload config file written by EP
                    self.loadConfig()
                    # On resume, stop waiting
                    if self.CONFIG['STATUS'] == 'running' or self.CONFIG['STATUS'] == 'resume':
                        self.proxy.echo(':: {} is no longer paused !'.format(self.epName))
                        break
                    # On stop...
                    elif self.CONFIG['STATUS'] == 'stopped':
                        # When a test is waiting for resume, but receives STOP, send status NOT EXECUTED
                        Suicide('NOT EXECUTED: Status STOP, while waiting for resume!', file_id, STATUS_NOT_EXEC, 0.0)


            # If dependency file is PENDING or WORKING, wait for it to finish; for any other status, go next.
            if dependancy and self.proxy.getFileVariable(self.userName, dependancy, 'status') in [-1, False, STATUS_PENDING, STATUS_WORKING]:
                dep_suite = self.proxy.getFileVariable(self.userName, dependancy, 'suite')
                dep_file = self.proxy.getFileVariable(self.userName, dependancy, 'file')

                if dep_file:
                    self.proxy.echo(':: {} is waiting for file `{}::{}` to finish execution...'.format(self.epName, dep_suite, dep_file))
                    self.proxySetTestStatus(self.userName, file_id, STATUS_WAITING, 0.0) # Status WAITING

                    while 1:
                        time.sleep(3)
                        # Reload info about dependency file
                        if  self.proxy.getFileVariable(self.userName, dependancy, 'status') not in [-1, False, STATUS_PENDING, STATUS_WORKING]:
                            self.proxy.echo(':: {} is not longer waiting for dependency!'.format(self.epName))
                            break

                del dep_suite, dep_file


            # Download file from Central Engine!
            str_to_execute = self.proxy.getTestFile(self.userName, self.epName, file_id)

            # If CE sent False, it means the file is empty, does not exist, or it's not runnable.
            if str_to_execute == '':
                print('TC debug: File path `{}` does not exist!\n'.format(filename))
                if file_index == 0 and prerequisite:
                    abort_suite = suite_id
                    print('TC error: Prerequisite file for suite `{}` cannot run! No such file! All suite will be ABORTED!\n\n'.format(suite_name))
                self.proxySetTestStatus(file_id, STATUS_SKIPPED, 0.0) # Status SKIPPED
                print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                continue

            elif not str_to_execute:
                print('TC debug: File `{0}` will be skipped.\n'.format(filename))
                # Skipped prerequisite are ok, no need to abort.
                self.proxySetTestStatus(file_id, STATUS_SKIPPED, 0.0) # Status SKIPPED
                print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                continue


            file_ext = os.path.splitext(filename)[1].lower()

            # If file type is TCL
            if file_ext in ['.tcl']:
                if not self.runners['tcl']:
                    self.runners['tcl'] = TCRunTcl()
                current_runner = self.runners['tcl']

            # If file type is PERL
            elif file_ext in ['.plx']:
                if not self.runners['perl']:
                    self.runners['perl'] = TCRunPerl()
                current_runner = self.runners['perl']

            # If file type is PYTHON
            elif file_ext in ['.py', '.pyc', '.pyo']:
                if not self.runners['python']:
                    self.runners['python'] = TCRunPython()
                current_runner = self.runners['python']

            # Unknown file type
            else:
                print('TC warning: Extension type `{}` is unknown and will be ignored!'.format(file_ext))
                if file_index == 0 and prerequisite:
                    abort_suite = suite_id
                    print('TC error: Prerequisite file for suite `{}` cannot run! Unknown extension file! All suite will be ABORTED!\n\n'.format(suite_name))
                self.proxySetTestStatus(file_id, STATUS_NOT_EXEC, 0.0) # Status NOT_EXEC
                print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                continue


            # If there is a delay between tests, wait here
            if tc_delay:
                print('TC debug: Waiting {} seconds before starting the test...\n'.format(tc_delay))
                time.sleep(tc_delay)


            self.proxySetTestStatus(file_id, STATUS_WORKING, 0.0) # Status WORKING

            # Start counting test time
            timer_i = time.time()
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')

            result = None

            # --------------------------------------------------------------------------------------
            # RUN CURRENT TEST!
            try:
                globs = {
                    'userName': self.userName,
                    'epName':   self.epName,
                    'tbName':   self.tbName,
                    'suite_id'  : suite_id,
                    'suite_name': suite_name,
                    'file_id'   : file_id,
                    'filename'  : filename,
                    'proxy'     : self.proxy,
                    'logMsg'    : self.logMsg,
                    'getGlobal' : self.getGlobal,
                    'setGlobal' : self.setGlobal,
                    'py_exec'   : self.py_exec
                }
                result = current_runner._eval(str_to_execute, globs, args)
                result = str(result).upper()
                print('\n>>> File `{}` returned `{}`. <<<\n'.format(filename, result))

            except Exception, e:
                # On error, print the error message, but don't exit
                print('\nException:')
                print(traceback.format_exc())
                print('\n>>> File `{}` execution CRASHED. <<<\n'.format(filename))

                self.proxy.echo('TC error: Error executing file `{}`!'.format(filename))
                self.proxySetTestStatus(file_id, STATUS_FAIL, (time.time() - timer_i))

                # If status is FAIL and the file is not Optional and Exit on test fail is ON, CLOSE the runner
                if not optional_test and exit_on_test_fail:
                    print('TC error: Mandatory file `{}` returned FAIL! Closing the runner!\n\n'.format(filename))
                    self.proxy.echo('TC error: Mandatory file `{}::{}::{}` returned FAIL! Closing the runner!'\
                        ''.format(self.epName, suite_name, filename))
                    print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                    exit(1)

                # If status is FAIL, and the file is prerequisite, CANCEL all suite
                if file_index == 0 and prerequisite:
                    abort_suite = suite_id
                    print('TC error: Prerequisite file for suite `{}` returned FAIL! All suite will be ABORTED!\n\n'.format(suite_name))
                    self.proxy.echo('TC error: Prerequisite file for `{}::{}` returned FAIL! All suite will be ABORTED!'\
                        ''.format(self.epName, suite_name))

                # Send crash detected = True
                self.proxy.setFileVariable(self.userName, self.epName, file_id, 'twister_tc_crash_detected', 1)
                print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                continue

            # Stop counting time. END OF TEST!
            timer_f = time.time() - timer_i
            end_time = time.strftime('%Y-%m-%d %H:%M:%S')
            # --------------------------------------------------------------------------------------


            print('Test statistics: Start time {} -- End time {} -- {:0.2f} sec.\n'.format(start_time, end_time, timer_f))

            if result==STATUS_PASS or result == 'PASS':
                self.proxySetTestStatus(file_id, STATUS_PASS, timer_f) # File status PASS
            elif result==STATUS_SKIPPED or result in ['SKIP', 'SKIPPED']:
                self.proxySetTestStatus(file_id, STATUS_SKIPPED, timer_f) # File status SKIPPED
            elif result==STATUS_ABORTED or result in ['ABORT', 'ABORTED']:
                self.proxySetTestStatus(file_id, STATUS_ABORTED, timer_f) # File status ABORTED
            elif result==STATUS_NOT_EXEC or result in ['NOT-EXEC', 'NOT EXEC', 'NOT EXECUTED']:
                self.proxySetTestStatus(file_id, STATUS_NOT_EXEC, timer_f) # File status NOT_EXEC
            elif result==STATUS_TIMEOUT or result == 'TIMEOUT':
                self.proxySetTestStatus(file_id, STATUS_TIMEOUT, timer_f) # File status TIMEOUT
            elif result==STATUS_INVALID or result == 'INVALID':
                self.proxySetTestStatus(file_id, STATUS_INVALID, timer_f) # File status INVALID
            else:
                self.proxySetTestStatus(file_id, STATUS_FAIL, timer_f) # File status FAIL

                # If status is FAIL and the file is not Optional and Exit on test fail is ON, CLOSE the runner
                if not optional_test and exit_on_test_fail:
                    print('TC error: Mandatory file `{}` returned FAIL! Closing the runner!\n\n'.format(filename))
                    self.proxy.echo('TC error: Mandatory file `{}::{}::{}` returned FAIL! Closing the runner!'\
                        ''.format(self.epName, suite_name, filename))
                    print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))
                    exit(1)

                # If status is FAIL, and the file is prerequisite, CANCEL all suite
                if file_index == 0 and prerequisite:
                    abort_suite = suite_id
                    print('TC error: Prerequisite file for suite `{}` returned FAIL! All suite will be ABORTED!\n\n'.format(suite_name))
                    self.proxy.echo('TC error: Prerequisite file for `{}::{}` returned FAIL! All suite will be ABORTED!'\
                        ''.format(self.epName, suite_name))


            print('<<< END filename: `{}:{}` >>>\n'.format(file_id, filename))

            sys.stdout.flush() # Flush just in case

            #---------------------------------------------------------------------------------------

        print('\n===== ===== ===== =====')
        print('. . . All tests done . . .')
        print('===== ===== ===== =====\n')


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


if __name__=='__main__':

    userName   = sys.argv[1:2]
    epName = sys.argv[2:3]

    if not userName:
        print('TC error: TestCaseRunner must be started with username argument! Exiting!')
        exit(1)
    else:
        userName = userName[0]
    if not epName:
        print('TC error: TestCaseRunner must be started with EpName argument! Exiting!')
        exit(1)
    else:
        epName = epName[0]
        print('TC debug: TestCaseRunner started with  User: {} ;  EP: {}.'.format(userName, epName))

    runner = TwisterRunner(userName, epName)

    runner.run()


# # #
