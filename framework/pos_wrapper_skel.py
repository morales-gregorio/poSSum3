#!/usr/bin/python
import sys
import os
import multiprocessing

import time
import datetime
import logging
from optparse import OptionParser, OptionGroup

import pos_wrappers
import pos_common


class generic_workflow(object):
    """
    A generic command-line workflow class. Workflow should be understood as a
    configurable pipeline with a configurable execution settings.

    The workflow / pipeline may consist of different stages use a numbser of
    different files, etc. The reason for this class is to use command line tools
    which functionality cannot be achieved in any other way.
    """

    # _f is a dictionary holding definitions of files beeing a part of the
    # workflow. The purpose of this dictionary is to be able to easily access
    # and utilize filenames (from each stage of the workflow). You're gonna like
    # it.
    _f = {}

    # Override this attribute in the inherited classes.
    _usage = ""

    def __init__(self, options, args):
        self.options = options
        self.args = args

        # Just an alias that assigns private attribute as a public. May be
        # changed in the future.
        self.f = dict(self._f)

        # Get number of cpus for parallel processing.
        # Multiprocessing modlue is used to determine the number of cpus. This
        # behavior can be overriden with --cpuNo switch.
        if not self.options.cpuNo:
            self.options.cpuNo = multiprocessing.cpu_count()

        self._initializeLogging()
        self._initializeOptions()
        self._validateOptions()
        self._initializeDirectories()
        self._overrideDefaults()

    def _initializeLogging(self):
        """
        Seems to be self explaining - initialized the logging module using
        either ethe default logging settings or customized logging settings
        according to provided command line paramteres.
        """
        pos_common.setup_logging(self.options.logFilename,
                      self.options.loglevel)

        logging.debug("Logging module initialized. Saving to: %s, Loglevel: %s",
                      self.options.logFilename, self.options.loglevel)

        # Assign the the string that will identify all messages from this
        # script
        self._logger = logging.getLogger(self.__class__.__name__)

        self._logger.info("%s workflow options:", self.__class__.__name__)
        for k,v in self.options.__dict__.items():
            self._logger.info("%s : %s", k, v)

    def _initializeOptions(self):
        """
        There is not many to process or initialize. Actually only jobID (if not
        provided) is processed automatically.
        """

        # What the heck is a "specimen ID"? It is supposed to be at least single
        # value which will allow to assign an instance of the workflow to
        # particual animal. When you have multiple animals they can get
        # confused easily. In the future, specimen ID, will act as database ID
        # for given specimen. Thus, it is hardcoded to not allow any
        # computations without this ID. Simple as it is.
        try:
            self.options.specimenId
        except:
            print >>sys.stderr, "No specimen ID provided. Please provide a specimen ID."
            sys.exit(1)

        # Job ID is another value for accointing and managing. Oppoosite to the
        # specimen ID, this one may not be explicitly stated. In that case, it
        # is generated automatically based on current data and PID.
        if self.options.jobId is None:
            self.options.jobId = self.__class__.__name__
            self.options.jobId += datetime.datetime.now().strftime("_%Y-%m-%d-%H_%M-%S_")
            self.options.jobId += str(os.getpid())

    def _overrideDefaults(self):
        """
        A generic function for altering configuration that was set with
        default values. Should be reimplemented in subclasses.
        """
        pass

    def _validateOptions(self):
        """
        A generic command line options validation function. Should be customized
        in subclasses. A lot of assertions is expected to be here!
        """
        pass

    def _initializeDirectories(self):
        """
        """
        # The directiories in the dictionary below are the potential working
        # dirs for the workflow. The 'sharedbf' is used when given mashine
        # has a ramdisk, otherwise 'tempbf'. These are the default locations for
        # the workdir. Typically, the working directory location is a custom
        # one.
        _dirTemplates = {
                'sharedbf': '/dev/shm/',
                'tempbf'  : '/tmp/',
                }

        # That's clever idea: When one don't want (or cannot) use shared memory
        # on given mashine, the regular /tmp/ directory is used to support the computations.
        # The tmp directory can be also set manually to, e.g., directory shared
        # among whole computer cluster.
        if self.options.disableSharedMemory:
            top_directory = self._dirTemplates['tempbf']
        else:
            top_directory = self._dirTemplates['sharedbf']

        # If the working directory (the directory holding all the
        # job's calculations) is not defined, we define it automatically
        # When the working directory name IS provided we just use it.
        if not self.options.workdir:
            self.options.workdir = os.path.join(top_directory, self.options.jobId)
        self._ensureDir(self.options.workdir)

        # Assign path to work dir to all templates:
        for k, v in self.f.iteritems():
            v.job_dir = self.options.workdir

        # And, as a last point, just create the directories.
        dirs_to_create = list(set(map(lambda v: v.base_dir,  self.f.itervalues())))
        map(self._ensureDir, dirs_to_create)

    def _ensureDir(self, path):
        """
        Makes sure that the given directory exists and is avalilable.

        :param path: Location to be tested. Note that only directory names are
        valid paths. Passing filenames will probably end badly...
        :type path: str
        """
        return pos_wrappers.mkdir_wrapper(dir_list=[path])()

    def _rmdir(self, path):
        """
        Removes given location. Watch out as the files and/or directories are
        removed recursively and uninvertabely (as in `rm -rfv` command).

        :param path: Location to be removed.
        :type path: str
        """
        return pos_wrappers.rmdir_wrapper(dir_list=[path])()

    @staticmethod
    def _basesame(path, withExtension=False):
        return pos_common.get_basename(path, withExtension)

    def _clean_up(self, immediate=False):
        """
        Erases the job's working directory.

        #TODO:

        .. warninig: The `immediate` switch is not implemented as of yet.

        :param immediate: Decides if the job's working directory will be erased
        immediately or as a last step of the workflow.
        :type immediate: bool
        """
        self._rmdir(self.options.workdir)

    def execute(self, commands, parallel=True):
        """
        One of the most important methods in the whole class. Executes the
        workflow. The execution can be launched in parallel mode, and / or in
        the 'dry run' mode. With the latter, the commands to be executed are actually only printed.
        The 'dry run' mode is selected / deselected using command line workflow settings.

        :param commands: The commands to be executed
        :type commands: An interable (in case of multiple commands - the usual case), a string in case of a singe command.

        :param parallel: Enables execution in parallel mode
        :type parallel: bool
        """

        #TODO: Implement pbs job dependencies
        # (https://docs.loni.org/wiki/PBS_Job_Chains_and_Dependencies)

        # If single command is provided, it is supposed to be a string. Convert
        # to list with a single element.
        if not hasattr(commands, "__getitem__"):
            commands = [commands]

        # In the regular execution mode (no dry-run) the commands can be
        # executed serially or parallelly. In the latter case, all the commands
        # are dumped into a file and executed with the GNU parallel.
        if not self.options.dryRun:
            if parallel:
                command_filename = os.path.join(self.options.workdir, str(time.time()))
                open(command_filename, 'w').write("\n".join(map(str, commands)))
                os.system('cat %s | parallel -k -j %d ' %
                        (command_filename, self.options.cpuNo))
            else:
                map(lambda x: x(), commands)
        else:
            print "\n".join(map(str, commands))

    def execute_callable(self, command):
        """
        Immediately executes the command.

        .. deprecated:: 0.1
           Redundant. The same effect can be achieved by
           invoking :py:func:`self.execute(command, parallel=False)`.

        .. todo::
           TODO: Please find
           all invocations of this function and replace them.

        :param command: Command to be executed.
        :type command: :py:class:`pos_wrappers.generic_wrapper`
        """

        self.execute(command, parallel=False)

    @classmethod
    def _getCommandLineParser(cls):
        """
        """
        parser = OptionParser(usage=cls._usage)

        workflowSettings = OptionGroup(parser, 'General workflow settings')
        workflowSettings.add_option('--jobId', '-j', dest='jobId', type='str',
                default=None, help='Job identifier. An optional value identyfying this particular workflow. If ommited, the jobId will be generated automatically.')
        workflowSettings.add_option('--workDir', '-d', dest='workdir', type='str',
                default=None, help='Sets the working directory of the process. Overrides the "--disableSharedMemory" switch.')
        workflowSettings.add_option('--loglevel', dest='loglevel', type='str',
                default='WARNING', help='Loglevel: CRITICAL | ERROR | WARNING | INFO | DEBUG')
        workflowSettings.add_option('--logFilename', dest='logFilename',
                default=None, action='store', type='str',
                help='Sets dumping the execution log file instead stderr')
        workflowSettings.add_option('--cleanup', default=False,
                dest='cleanup', action='store_const', const=True,
                help='Remove the worklfow directory after calculations. Use when you are sure that the workflow will execute correctly.')
        workflowSettings.add_option('--disableSharedMemory', default=False,
            dest='disableSharedMemory', action='store_const', const=True,
            help='Forces script to use hard drive to store the worklfow data instaed of using RAM disk.')
        workflowSettings.add_option('--specimenId', '-s', default=None,
                dest='specimenId', action='store', type='str',
                help='Identifier of the specimen. Providing the ID is obligatory. Script will not run without providing specimen ID.')
        workflowSettings.add_option('--dryRun', default=False,
                action='store_const', const=True, dest='dryRun',
                help='Prints the commands to stdout instead of executing them')
        workflowSettings.add_option('--cpuNo', '-n', default=None,
                type='int', dest='cpuNo',
                help='Set a number of CPUs for parallel processing. If skipped, the number of CPUs will be automatically detected.')

        parser.add_option_group(workflowSettings)
        return parser

    @classmethod
    def parseArgs(cls):
        parser = cls._getCommandLineParser()
        (options, args) = parser.parse_args()
        return (options, args)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
