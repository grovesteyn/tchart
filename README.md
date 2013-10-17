tchart
======

Python reporting and front-end for Taskwarrior.

Tchart adds the following functionality to Taskwarrior:

1) It provides a task report along the basic lines of a GANTT chart using task due dates.  Overdue tasks are indicated in red, the current day's tasks in yellow and the rest in the normal font.  Tasks are indented in accordance with their due dates.  Tasks with a high priority are shown in capital letters.  Tasks from the same project are grouped together for each date.  The number of tasks shown is selected to fill the available screen space.

Overall the intention is to provide a visual overview of my TODO list that is an improvement on what is available from Taskwarrior.

2) It provides a listbox selection tool to allow rapid updates of the task list (by using the -s switch).  Onscreen buttons, or hotkeys allow rapid changes to selected task due dates; marking tasks as complete; or by completing the Taskwarrior commandline.

It is also possible to add specific task filters after the -s switch.

Being an amateur programmer I would welcome contributions and improvements.
