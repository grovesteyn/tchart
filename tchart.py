#!/usr/bin/env python3

"""
This programme presents Taskwarrior tasks as a GANTT chart and provides a menu
selector.  It allows tasks to be filtered.  Use tcal --help for instructions
"""

from email.policy import strict
import pdb, json, subprocess, subprocess, argparse
import snack  # On Ubuntu do apt-get install python-newt to get snack module
from datetime import datetime, timedelta, date
from dateutil import parser  # sudo pip install python-dateutil
import time
from subprocess import PIPE, Popen
from blessings import Terminal  # sudo pip install blessings
# On Ubuntu do: sudo apt-get install python-blessings
# from IPython.core.debugger import Tracer
import warnings
warnings.filterwarnings("ignore")  # This is not the best practice, but a hack for now. Can refine to 
                                  #  only pick up the snack warning problem.


class TaskReport(object):
    """This is the main class for this programme."""

    def __init__(self):

        self.weeks = 5  # Number of weeks to cover. Was 4.
        self.weekstart = date.today() - timedelta(date.weekday(date.today()))
        self.cutoffdate = self.weekstart + timedelta(weeks=self.weeks)
        self.construct_cmdline()
        self.load_tasks()

        #        Call the appropriate function to either run the task selector,
        #        or print the task report to the console.

        if self.selector:
            # TODO Move this while loop into selectorresult
            while True:
                selectorresult = self.run_selector()
                if selectorresult[1]:
                    break
                #                print (selectorresult[0])
                self.load_tasks() # This is here for the second and subsequent loops
        else:
            self.run_report()

    def construct_cmdline(self):
        """
        Construct the Taskwarrior commandline to be used.
        """

        parser = argparse.ArgumentParser(description='Display tasks.')
        parser.add_argument("-s", "--select", action="store_true",
                            help="Select tasks and modify")
        parser.add_argument("-p", "--byproject", action="store_true",
                            help="Sort tasks by proj before sorting by date")
        parser.add_argument("-l", "--list", action="store_true",
                            help="Do not use GANTT display mode, use list mode.")
        parser.add_argument("-f", "--filter", nargs='+',
                            help='a string specifying the task filter')
        args = parser.parse_args()
        #        if args.select:
        #            print "select tasks"
        
        #  Check for Taskwarrior context and implement it

        curcontext = subprocess.getoutput('task _get rc.context').splitlines()[0]
        if curcontext != '':
            curcontextfilter = subprocess.getoutput('task _get rc.context.' + curcontext + '.read').splitlines()[0]
            self.consoleline = '\'(' + curcontextfilter + ')\' '
        else:
            self.consoleline = ''
        
        if args.filter:
            self.consoleline = self.consoleline + " ".join(args.filter)
            self.consoleline = (self.consoleline + ' status:pending') \
                if (self.consoleline.find('status:') < 0
                    and self.consoleline.find('status.') < 0) \
                else self.consoleline
            # self.consoleline = (self.consoleline + ' due.any:') \
            #     if (self.consoleline.find('due:') < 0
            #         and self.consoleline.find('due.') < 0) \
            #     else self.consoleline
            self.consoleline = self.consoleline + ' export' \
                if self.consoleline.find('export') < 0 else self.consoleline
        else:
            # When no arguments are given.
            self.consoleline = self.consoleline + 'due.any: status:pending export'
            # self.consoleline = self.consoleline + ' tags.not:adam and tags.not:leenesh and tags.not:alison'

        self.consoleline = self.consoleline + ' rc.verbose:nothing'
            # rc.verbose:nothing to avoid any comments in output
        self.consoleline = "task " + self.consoleline
            # In quotes to allow backets in filter
        self.selector = args.select
        self.byproject = args.byproject
        self.list = args.list
        print((self.consoleline))
        if curcontext:
            print ('\033[5m' + "Context: "+ curcontext + '\033[0m')
        else:
            print ("No Context")

    def load_tasks(self):
        """
        Load and sort the task list
        """
        # subprocess.call(self.consoleline.split())  # This is the python way
        tstring = subprocess.getoutput(self.consoleline)
        #cmdlist = list(self.consoleline.split(" "))
        #tstring = subprocess.check_output(cmdlist) 
        # with open("Output.txt", "w") as text_file:
        #     text_file.write(tstring)  # Was used to debug problems with json output from task

        # tstring = '[' + tstring + ']'  # Adds brackets to comply with Json
        # tstring = tstring.replace('\n',',\n')
        # print (repr(tstring))  # Show the newline characters, etc.
        # print(tstring.splitlines()[21:23])
        tasks = json.loads(tstring)  # Ensure json.array=on in .taskrc
        # This section removes the tasks with no due dates and adds them to the
        # front of the list after it has been sorted by due date and project

        due_list = []
        nodue_list = []
        for task in tasks:
            if ('due' not in task):  # or (task['priority']=='H' if 'priority' in task else False):
                # Fix the added code to place priority = H tasks at top of listing.
                nodue_list.append(task)
            else:
                offset = time.timezone if (time.localtime().tm_isdst == 0) \
                    else time.altzone
                task["due"] = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ") \
                    - timedelta(seconds=offset)  # To local time object
                due_list.append(task)
        tasks = due_list

        try:
            if self.list:
                tasks = nodue_list + tasks
                tasks.sort(key=lambda x: (x['project']))
            elif self.byproject:
                tasks.sort(key=lambda x: (x['project'].split('.')[0],
                                          x['due'].date()))
                tasks = nodue_list + tasks
            else:  # Normal GANTT mode
                tasks.sort(key=lambda x: (x['due'].date(), x['project']))
                tasks = nodue_list + tasks
        except KeyError:  # If no 'project' attribute for one or more tasks
            # tasks.sort(key=itemgetter('due'))
            tasks.sort(key=lambda x: (x['due']))
            tasks = nodue_list + tasks
            self.noproject = True

        self.tasks = tasks

    def run_report(self):
        """
        Compile and print the task report.
        """
        wdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        letters = 3  # No of letters to use for wday names. 1 - 3
        istty = True
        indent = letters  # The indent per week day
        # TODO "indent" is used and defined here and in construct_cmdline.  Define once?
        if istty:  # This is currently hard coded, but can be an input.
            term = Terminal()
        else:
            term = Terminal(stream="not tty")  # When not run from a tty
        # Calcs how many task lines can fit onto the screen.
        # taskspace = (term.height if term.is_a_tty else 40) - (5 + letters)
        taskspace = (term.height if term.is_a_tty and not self.list else 200 if self.list else 40) - (5 + letters)
        # Compile the line showing each Monday's date.
        self.width = term.width
        try:
            self.weeks = int(self.width / (3 * 7))
        except TypeError:
            self.weeks = self.weeks  # TODO Remove the specification at __init__
        dateline = self.weekstart.strftime("%d %b %Y")
        if self.weeks > 1:  # Add additional Mondays if required
            for week in range(1, self.weeks):  # i.e. week 1 is the second week.
                # No of spaces to add on to existing dateline before
                # inserting next date
                weekindent = len(wdays) * week * indent - len(dateline)
                dateline = dateline + ' ' * weekindent + (self.weekstart +
                                                          timedelta(days=7 * week)).strftime("%d %b %Y")  # Position

        # Compile the day header sting (includes newlines)
        dayheader = ''
        for lineNo in range(letters):
            for day in wdays * self.weeks:
                #  add the letter and spacing to indent for each day and makes mondays bold
                dayheader = dayheader + (term.bold(day[lineNo]) if (day == \
                    "MON" and not self.selector) else day[lineNo]) + ' ' \
                    * (indent - 1)
            dayheader = dayheader + '\n'

        # Compile the multiline string containing the tasklines
        projname = ""  # Used to track project names if sorted by projec (i.e. self.byproject=True)
        taskstring = ""
        for task in self.tasks:  # Step through list of task dictionary objects
            if (self.byproject) and ("project" in task):
                if task["project"] != projname:
                    projname = task["project"]
                    taskstring = taskstring + (2*'\n' if self.list else '\n') + term.underline(projname.capitalize())

            taskline, tdate = self.compile_taskline(task)
            
            if ("priority" in task and task["priority"] == "H"):
                taskline = term.bold(taskline)
            
            if tdate.date() < date.today():
                if ("priority" in task and task["priority"] == "H"):
                    # Add newline if not end of list and colour red
                    taskstring = taskstring + ('\n' if len(taskstring) != 0 else ''
                                            ) + term.bright_red_blink(taskline)
                else:
                    # Add newline if not end of list and colour red
                    taskstring = taskstring + ('\n' if len(taskstring) != 0 else ''
                                            ) + term.bright_red(taskline)
            elif tdate.date() == date.today():
                taskstring = taskstring + '\n' + term.green(taskline)
            elif tdate.date() > date.today():
                taskstring = taskstring + '\n' + taskline

        # Removes lines that will not fit onto screen
        terminal_lines = ''.join(taskstring.splitlines(True)[0:taskspace])
        terminal_lines = terminal_lines[1:]  # Remove first newline

        if getattr(self, 'noproject', False):
            print ("WARNING: Some tasks do not have a project assigned. "
                   "Tasks will not be properly grouped by project")
        print(('\n' + dateline + '\n' + dayheader + terminal_lines))

    def run_selector(self):
        """
        Compile and run the task selector.

        See: http://www.wanware.com/tsgdocs/snack.html https://pagure.io/newt for info on the
        python snack module.
        Also look at the code in snack.py to understand what it is doing.
        @rtype : Tupple with return from running the command and a bool
        indicator of whether to quit.

        TODO: Convert to npyscreen.
        Start at https://pypi.python.org/pypi/npyscreen/
        and http://npyscreen.readthedocs.org/index.html
        """
        wdays_short = "M  T  W  T  F  S  S  "

        extrahkeysdict = {'0': ' mod due:today',
                          '1': ' mod due:1d',
                          '2': ' mod due:2d',
                          '3': ' mod due:3d',
                          '4': ' mod due:4d',
                          '5': ' mod due:5d',
                          '6': ' mod due:6d',
                          '7': ' mod due:7d',
                          '8': ' mod due:1w',
                          '9': ' mod due:2w',
                          'd': ' done',
                          'r': ' rc.confirmation=false rm',
                          'i': ' info',
                          'h': ' HELP'
                          }

        for key in list(extrahkeysdict.keys()):
            snack.hotkeys[key] = ord(key)  # Add to the snack hkey library
            snack.hotkeys[ord(key)] = key

        #        Tracer()()
        screen = snack.SnackScreen()
        buttonlist = [("1d", "1d", "F1"),
                      ("2d", "2d", "F2"),
                      ("3d", "3d", "F3"),
                      ("1w", "1w", "F4"),
                      ("2w", "2w", "F5")
                      ]
        mybuttonbar = snack.ButtonBar(screen, buttonlist, 1)
         
        # t = snack.Textbox(width=10, height=1, text="Some text", scroll = 0, wrap = 0 )  #Trying too insert a line at bottom to show command line options
        
        lbox = snack.Listbox(height=20, width=111, returnExit=1, multiple=1,
                             border=1, scroll=1)  # width was 90
        
        
        for task in self.tasks:  # Step through list of task dictionary objects
            taskline, tdate = self.compile_taskline(task)
            lbox.append(taskline, task["id"])  # Unicode \
#            lbox.append(taskline.encode('utf-8'), task["id"])  # Unicode \
            # conversion fixes conversion to C issue. But not required in Python3

        grid = snack.GridForm(screen, wdays_short * self.weeks, 3, 3)
        # Note the padding option.  It is set to shift the lbox content one
        # position to the right so as to allign with the dayheader at the top
        grid.add(lbox, 0, 0, padding=(1, 0, 0, 0))
        grid.add(mybuttonbar, 0, 1, growx=1)
        grid.addHotKey('ESC')
        grid.addHotKey('q')
        # grid.addHotKey('j')
        # grid.addHotKey('k')
        for key in list(extrahkeysdict.keys()):
            grid.addHotKey(key)
        # grid.add(t)
        
        # FIXME Seems to crash here on second run. Fixed by only using screen.finish()
        # FIXME when completely done.
        #        Tracer()()
        result = grid.runOnce()
        buttonpressed = mybuttonbar.buttonPressed(result)  # The Hotkey dict \
        # value of key in 'result'.  Returns None if no hotkey or button \
        # pressed
        selection = lbox.getSelection()  # This is a list
        
        # The first set of if options deals with all the exceptions while \
        # the last 'else' deals with actual task manupulations.
        if result == 'ESC' or result == 'q':
            screen.finish()
            return (None, True)
        # elif result == 'j':  This section is to get the j and k keys to work as up and down in the listbox.  This might be the wrong
        #     pass             place to implement this.
        # elif result == 'k':
        #     pass
        elif result == 'h':
            mytext = ''
            for mykey in sorted(extrahkeysdict):
                mytext = mytext + '\n' + mykey + ': ' + extrahkeysdict[mykey]
            snack.ButtonChoiceWindow(screen, 'Help', mytext, ['Ok'])
            return (None, False)
        elif result == 'i':
            basictaskstr = 'task ' + str(lbox.current()) + ' info'
            mytext = subprocess.getoutput(basictaskstr)
            snack.ButtonChoiceWindow(screen, 'Task information', mytext,
                                     ['Ok'], width=80)
            return (None, False)
        else:
            # Get the selected or current task/s from the listbox
            if len(selection) > 0:
                # Joins the selections into comma seperated list, and suppresses
                # confirmation for this number of tasks
                # basictaskstr = 'task ' + ','.join(map(repr, lbox.getSelection())) \
                basictaskstr = 'task ' + ','.join(map(repr, selection)) \
                               + ' rc.bulk:' + str(len(selection) + 1)
            else:  # If no selections have been made use the current task
                basictaskstr = 'task ' + str(lbox.current())

            # Figure out what commands to add, if any given
            if buttonpressed:
                # TODO Change values in Buttonlist dict so that it provides the full command\
                # TODO so that it can be used in the same way as if any other hotkey was pressed
                basictaskstr = basictaskstr + ' mod due:' + buttonpressed
            elif result in extrahkeysdict:  # If a hotkey not linked to button.
                basictaskstr = basictaskstr + extrahkeysdict[result]
            else:  # Else type in the rest of the command.
                basictaskstr = basictaskstr + ' mod '

            result2 = snack.EntryWindow(screen, "Command details...",
                                        "", [('Command to be executed:', basictaskstr)], width=50,
                                        entryWidth=30, buttons=[('OK', 'OK', 'F1'), ('Cancel', 'Cancel',
                                                                                     'ESC')])  # Look at the code for function to understand this
            #screen.finish()
            if result2[0] == 'Cancel':
                return (None, False)
            else:

                p = Popen(result2[1][0].split(), stdin=PIPE, stderr=PIPE,
                          stdout=PIPE, bufsize=1, close_fds=True)
                output = p.communicate()

                # Also http://stackoverflow.com/questions/14457303/python-subprocess-and-user-interaction
                # The problem is to deal with situations when task wants further input from the
                # console, such as changing a due date of a recurring task.  Problem solved with
                # subprocess.communicate().
                # Can use fcntl to change bash console to unblocking mode and interact stepwise
                # as done here:
                # http://stackoverflow.com/questions/8980050/persistent-python-subprocess

                mystr = str(output[0],'utf-8') + str(output[1], 'utf-8')
                #screen.finish()
                #pdb.set_trace()
                snack.ButtonChoiceWindow(screen, 'Result', mystr, ['Ok'], width=80)
                return (output, False)

    def compile_taskline(self, task):

        """
        Compile a task line to be used in the task selector or in the
        task report.

        @type task: object
        @type annotation: dict

        """
        indent = 3  # The indent per week day

        if 'due' not in task:
            # Indents the task by 6 days at top of list to show that it does not \
            # have a due date.  datetime.min.time() is a constant for midnight
            tdate = datetime.combine(self.weekstart + timedelta(days=6), \
                                     datetime.min.time())  # Converts the date back to a datetime.
        else:
            #            tdate = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ") + \
            #                timedelta(seconds=time.timezone)  # Assume tasks are ordered by due date
            tdate = task['due']

        if self.list:
            daydiff = 0
        else:
            daydiff = tdate.date() - self.weekstart
            daydiff = daydiff.days

        taskline = indent * daydiff * " " + "(" \
                   + (task["project"] if "project" in task else "none") + ")" + " " \
                   + repr(task["id"]) + ("*" if "annotations" in task else " ") \
                   + ('[' + (', '.join(task["tags"]) + '] ') if 'tags' in task else '') \
                   + (task["description"].upper()
                      if ("priority" in task and task["priority"] == "H")
                      else task["description"]) \
                    + ' '
        
        # taskline = indent * daydiff * " " + "(" \
        #            + (task["project"] if "project" in task else "none") + ")" + " " \
        #            + repr(task["id"]) + ("*" if "annotations" in task else " ") \
        #            + (task["description"].upper()
        #               if ("priority" in task and task["priority"] == "H")
        #               else task["description"]) \
        #            + (' [' + (', '.join(task["tags"]) + ']') if 'tags' in task else '') + ' '

        if 'annotations' in task:
            for annotation in task['annotations']:
                annline = "\n  " + indent * daydiff * " "
                anndate = parser.parse(annotation['entry'])
                annline = annline + repr(anndate.year) + '-' + repr(anndate.month) + '-' + repr(anndate.day) + ' '
                annline = annline + annotation['description']
                taskline = taskline + annline


        #        try:
        #            taskline = taskline[0:self.width - 1]
        #        except TypeError:
        #            taskline = 80  # Remove the specification at __init__

        return taskline, tdate


def main():
    report = TaskReport()


if __name__ == '__main__':
    main()

"""
Done list

-   Numerous small fixes
-   Fixed time handling so that task due dates (especially the due day) are now
    correctly reflected.  This fixed a problem where a project's tasks on a
    specific were not always grouped together.
-   Fixed unicode error when using task selector (i.e. tchart -s)  This related
    to a problem with how unicode text was passed to the C snack module
    See: https://bugzilla.redhat.com/show_bug.cgi?id=689448
-   Added a -p switch that shows tasks sorted by project before due date.  This
    can do with some display improvement.  Works best when limited to smaller
    number of projects
-   Set the mast heading listing the weeks to screen width when doing a simple
    screen print of the tasks (i.e. using tchart with no options)
"""
