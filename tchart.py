#!/usr/bin/env python

# Read task output and organise by day

import pdb
import json
import commands
import argparse
import snack  # On Ubuntu do apt-get install python-newt to get snack module
from datetime import datetime, timedelta, date
from blessings import Terminal
from operator import itemgetter

class TaskReport(object):
    """
    This is the main class for this programme.
    """

    def __init__(self):

        self.weeks = 4  # Number of weeks to cover
        self.weekstart = date.today() - timedelta(date.weekday(date.today()))
        self.cutoffdate = self.weekstart + timedelta(weeks=self.weeks)
        self.construct_cmdline()
        self.load_tasks()

#        Call the appropriate function to either run the task selector,
#        or print the task report to the console.

        if self.selector:
            while True:
                selectorresult = self.run_selector()
                if selectorresult[1]:
                    break
                print selectorresult[0]
                self.load_tasks()

        else:
            self.run_report()

    def construct_cmdline(self):
        """
        Construct the Taskwarrior commandline to be used.
        """

        parser = argparse.ArgumentParser(description='Display tasks.')
        parser.add_argument("-s", "--select", action="store_true",
                            help="select tasks and modify")
        parser.add_argument("-f", "--filter", nargs='+',
                            help='a string specifying the task filter')
        args = parser.parse_args()
#        if args.select:
#            print "select tasks"
        if args.filter:
            self.consoleline = " ".join(args.filter)
            self.consoleline = (self.consoleline + ' status:pending') if \
                self.consoleline.find('status:pending') < 0 else \
                self.consoleline
            self.consoleline = (self.consoleline + ' export') if \
                self.consoleline.find('export') < 0 else self.consoleline
            self.consoleline = 'task ' + self.consoleline
        else:
            # Change the date format to match that required by Taskwarrior
            self.consoleline = 'task due.before:' + \
                str(self.cutoffdate).replace('-', '/') + ' status:pending ' + \
                '-erma export'
        #  Indicates whether task selector was requested.  Either True or None
        self.selector = args.select
        print self.consoleline
        print

    def load_tasks(self):
        """
        Load and sort the task list
        """
        tstring = commands.getoutput(self.consoleline)
        tstring = '[' + tstring + ']'  # Adds brackets to comply with Json
        tasks = json.loads(tstring)

        # This section removes the tasks with no due dates and adds them to the
        # front of the list after it has been sorted

        due_list = []
        nodue_list = []
        for task in tasks:
            if 'due' not in task:
                nodue_list.append(task)
            else:
                due_list.append(task)
        tasks = due_list

        try:
            tasks.sort(key=itemgetter('due', 'project'))
        except KeyError:  # If no 'project' attribute for one or more tasks
            tasks.sort(key=itemgetter('due'))
            print "Warning: Some tasks do not have a project assigned."
        self.tasks = nodue_list + tasks

    def run_report(self):
        """
        Compile and print the task report.
        """
        wdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        letters = 3     # No of letters to use for wday names. 1 - 3
        istty = True
        indent = letters      # The indent per week day
# TODO "indent" is used and defined here an in construct_cmdline.  Define once?
        if istty:  # This is currently hard coded, but can be an input.
            term = Terminal()
        else:
            term = Terminal(stream="not tty")  # When not run from a tty
        # Calcs how many task lines can fit onto the screen.
        taskspace = (term.height if term.is_a_tty else 40) - (5 + letters)
        # Compile the line showing each Monday's date.
        dateline = self.weekstart.strftime("%d %b %Y")
        if self.weeks > 1:  # Add additional Mondays if required
            for week in range(1, self.weeks):  # i.e. week 1 is the second week.
                # No of spaces to add on to existing dateline before
                # inserting next date
                weekindent = len(wdays) * week * indent - len(dateline)
                dateline = dateline + ' ' * weekindent + (self.weekstart + \
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
        taskstring = ""
        for task in self.tasks:   # Step through list of task dictionary objects
            taskline, tdate = self.compile_taskline(task)
            if tdate.date() < date.today():
                # Add newline if not end of list and colour red
                taskstring = taskstring + ('\n' if len(taskstring) != 0 else ''
                    ) + term.red(taskline)
            elif tdate.date() == date.today():
                taskstring = taskstring + '\n' + term.yellow(taskline)
            elif tdate.date() > date.today():
                taskstring = taskstring + '\n' + taskline

        # Removes lines that will not fit onto screen
        terminal_lines = ''.join(taskstring.splitlines(True)[0:taskspace])
        print dateline + '\n' + dayheader + terminal_lines

    def run_selector(self):
        """
        Compile and run the task selector.
        
        See: http://www.wanware.com/tsgdocs/snack.html for info on the
        python snack module.
        Also look at the code in snack.py to understand what it is doing.
        """
        wdays_short = "M  T  W  T  F  S  S  "

        extrahkeysdict = {'1': ' mod due:1d',
                          '2': ' mod due:2d',
                          '3': ' mod due:3d',
                          '4': ' mod due:4d',
                          '5': ' mod due:5d',
                          '6': ' mod due:6d',
                          '7': ' mod due:7d',
                          '8': ' mod due:1w',
                          '9': ' mod due:2w',
                          '0': ' mod due:today',
                          'd': ' done'}

        for key in extrahkeysdict.keys():
            snack.hotkeys[key] = ord(key)  # Add to the snack hkey library
            snack.hotkeys[ord(key)] = key
        screen = snack.SnackScreen()
        buttonlist = [("1d", "1d", "F1"),
                      ("2d", "2d", "F2"),
                      ("3d", "3d", "F3"),
                      ("1w", "1w", "F4"),
                      ("2w", "2w", "F5")
                      ]
        mybuttonbar = snack.ButtonBar(screen, buttonlist, 1)
        lbox = snack.Listbox(height=20, width=90, returnExit=1, multiple=1,
                             border=1, scroll=1)
        for task in self.tasks:  # Step through list of task dictionary objects
            taskline, tdate = self.compile_taskline(task)
            lbox.append(taskline, task["id"])
        grid = snack.GridForm(screen, wdays_short * self.weeks, 3, 3)
        # Note the padding option.  It is set to shift the lbox content one
        # position to the right so as to allign with the dayheader at the top
        grid.add(lbox, 0, 0, padding=(1, 0, 0, 0))
        grid.add(mybuttonbar, 0, 1, growx=1)
        grid.addHotKey('ESC')
        for key in extrahkeysdict.keys():
            grid.addHotKey(key)
        result = grid.runOnce()
        buttonpressed = mybuttonbar.buttonPressed(result)
        selection = lbox.getSelection()

        if result == 'ESC':
            screen.finish()
            return (None, True)

        # Get the selected or current task/s from the listbox
        if len(selection) > 0:
            # Joins the selections into comma seperated list, and suppresses
            # confirmation for this number of tasks
            basictaskstr = 'task ' + ','.join(map(repr, lbox.getSelection())) \
                + ' rc.bulk:' + str(len(lbox.getSelection()) + 1)
        else:  # If no selections have been made use the current task
            basictaskstr = basictaskstr = 'task ' + str(lbox.current())

        # Figure out what commands to add, if any given
        if buttonpressed:
            basictaskstr = basictaskstr + ' mod due:' + buttonpressed
        elif result in extrahkeysdict: # If a hotkey not linked to button.
            basictaskstr = basictaskstr + extrahkeysdict[result]
        else:  # Else type in the reset of the command.
            basictaskstr = basictaskstr + ' mod '

        result = snack.EntryWindow(screen, "Enter command details...", \
            "", [('Command to be executed:', basictaskstr)], width=50, \
            entryWidth=30, buttons=[('OK', 'OK', 'F1'), ('Cancel', 'Cancel',
            'ESC')])  # Look at the code for this function to understand this
        screen.finish()
        if result[0] == 'Cancel':
            return(None, True)
        else:
            print '>' + result[1][0]
            return (commands.getoutput(result[1][0]), False)

    def compile_taskline(self, task):
        """
        Compile a task line to be used in the task selector or in the
        task report.
        """
        indent = 3      # The indent per week day

        if 'due' not in task:
        # Indents the task by 6 days at top of list to show that it does not \
        # have a due date.  datetime.min.time() is a constant for midnight
            tdate = datetime.combine(self.weekstart + timedelta(days=6), \
                datetime.min.time())  # Converts the date back to a datetime.

        else:
            tdate = datetime.strptime(task["due"], "%Y%m%dT%H%M%SZ") + \
                timedelta(hours=2)  # Assume tasks are ordered by due date
        daydiff = tdate.date() - self.weekstart
        daydiff = daydiff.days
        taskline = indent * daydiff * " " + repr(task["id"]) + " (" + \
            (task["project"] if "project" in task else "none") \
            + ")" + ("*" if "annotations" in task else " ") \
            + (task["description"].upper()
            if ("priority" in task and task["priority"] == "H")
            else task["description"])
        return taskline, tdate


def main():
    report = TaskReport()

if __name__ == '__main__':
    main()
