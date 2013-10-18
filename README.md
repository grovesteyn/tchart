tchart
======

Python reporting and front-end for Taskwarrior.


Tchart provides a GANTT type report and rapid-use listbox task selection and modification tool for Taskwarrior.  

Invocation
----------
If tchart is invoked without any switches it displays the GANTT-type report and exits.

Using the -f (or --filter=FILTER) switch allows specific task filters to be specified.

Using the -s (or --selector) switch invokes the listbox task selection and modification screens.

GANTT-type report
-----------------

The GANTT report looks like this:

<pre>
task -temp due.before:2wks -erma status:pending export

14 Oct 2013          21 Oct 2013          28 Oct 2013          04 Nov 2013
M  T  W  T  F  S  S  M  T  W  T  F  S  S  M  T  W  T  F  S  S  M  T  W  T  F  S  S  
O  U  E  H  R  A  U  O  U  E  H  R  A  U  O  U  E  H  R  A  U  O  U  E  H  R  A  U  
N  E  D  U  I  T  N  N  E  D  U  I  T  N  N  E  D  U  I  T  N  N  E  D  U  I  T  N  

         37 (w-rompco.application) ROMPCO UPDATED NERSA APPLICATION
         70 (w-tips-regulation) Kry datum vir TIPS regulation forum and berei voor
         60 (wadmin)*FINALISEER MEPTY BTW NOMMER
         62 (wadmin) Kyk na epos van PKF oor stappe om ME BTW registrasie te doen
         87 (w-strat) LEES TELEKOMS GOED.
         84 (w-tips-regulation) TIPS KONTRAK
         78 (wadmin) Request people to act as referenences
            71 (pers) LEES ERMA SE OPSTELLE
            30 (wadmin) BETAAL VIR LOMBARD VIR DIE BANDWIDTH
            40 (wadmin) REVIEW MANAGEMENT ACCOUNTS
            35 (wadmin.tax) Renew tax clearance certificate
               92 (pers) draf
               74 (wadmin) DOEN BTW
                        83 (w-tips-regulation) Berei seminaar voor vir TIPS
                           17 (wadmin) Combine all sent emails in one place
                              29 (aviation) Doen vlieg medies

</pre>


Overdue tasks are indicated in red, the current day's tasks in yellow and the rest in the normal font.  Tasks are indented in accordance with their due dates.  Tasks with priority set to "high" are shown in capital letters.  Tasks that have annotations attached have a '*' in front of their name.  Tasks from the same project are grouped together for each date.  The number of tasks shown is selected to fill the available screen space.

Overall the intention is to provide a visual overview of my TODO list that is an improvement on what is available from Taskwarrior.

Listbox task selection and modification
---------------------------------------

The listbox selection tool allows rapid updates of the task list (by using the -s switch).  Onscreen buttons, or hotkeys allow rapid changes to selected tasks' due dates; marking tasks as complete; or an easy way to completing the Taskwarrior commandline for the selected tasks.

- Tasks are selected with the spacebar.  If no selection is made the task under the cursor is used.
- Keys 1 - 7 sets the due date 1 - 7 days into the future (e.g. key '2' executes 'task 22 mod due:2')
- 0 sets the due date to today
- d marks tasks as 'done'

Pressing any hotkey or hitting Enter after selecting (a) task/s moves to the next screen.  Tchart compiles the appropriate TW commandline and displays it for approval or modification (press Enter twice to execute the line).

Mode of use
-----------

I generally find that I use tchart in combination with the normal Taskwarrior commands.  I have also setup autocompletion to work with task, and with tchart, which futher increases its power.

Being an amateur programmer I would welcome contributions and improvements, and especially pull requests :-)) .
