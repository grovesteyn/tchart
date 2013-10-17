tchart
======

Python reporting and front-end for Taskwarrior.


Tchart provides a GANTT type report and rapid-use listbox task selection and modification tool for Taskwarrior.  The GANTT report looks like this:

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

The istbox selection tool allows rapid updates of the task list (by using the -s switch).  Onscreen buttons, or hotkeys allow rapid changes to selected tasks' due dates; marking tasks as complete; or an easy way to completing the Taskwarrior commandline for the selected tasks.

It is also possible to add specific task filters after the -f switch.

Being an amateur programmer I would welcome contributions and improvements.
