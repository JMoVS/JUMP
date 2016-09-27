For a better reading experience, consider reading the pdf. This measurement program is meant to be super-flexible, work with all your devices and generally help you with measuring. Because the way you record your data shouldn't be a problem, it's just a tool. How to build your appliances and interpret the data, that's where true value is added.

If you have feedback, ideas or questions, please feel free to contact me via email git@justinscholz.de or Twitter (@JMoVS).

---
Title:	JUMP Documentation  
Author:	Justin Scholz  
Date:	11.10.16
Quotes Language: german (de)
---

# JUMP, your medicine for great measurements! #

<!--TOC max2-->

# Inspired poetry

> Ease the pain
measurements now got fun
more knowledge to gain
great tests to run

> let's investigate this effect
we never saw it before
it'll earn us respect
as it won't be folklore

> The hardware shall abide
and power must not go out
so the sample shall ride
freed of all doubt

> It is protected there
safe but cold
so it may well fare
as the results be bold

> Stress is hard
the tremble's immense
but a breakthrough is in the card
it would all make perfect sense

> Breakthrough is here
there was no fear
remember DiBaMePro *(former name of this project)*
and the sample let go

> Because Tron is my ally! He always fights for the User.
>> --- The User

# Overview [Overview] #

JUMP is a program to perform (mainly dielectric) measurements and to control parameters of measurement setups. Its first showcase implementation includes the basics of how to make dielectric measurements with two hardware devices, *one* temperature controller (Lakeshore 336) and *one* measurement device, a Novocontrol ALPHA Analyzer.
The general design of JUMP aims to provide a platform to be easily able to handle more complex setups. It has five major design goals.

Usability (most important)
:	This (lab)-project aims to replace an existing QBasic program (not open source). It is tailored to our specific current needs. The QBasic program works and worked for 20 years. JUMP hopefully shows equal or better stamina. 

Extensibility
:	regarding the hardware devices and data processing. It should be easy to change parts of the program to extend them so that new tests and new measurement methods can run. Adding new measurement hardware or measurement setups should be a straight forward process.

Flexibility
:	regarding how and in which sequences data is gathered and when it is gathered concurrently. The user should be able to measure the way they want. This also implies that the user will be able to make non-sensical arrangements - but this is software aimed for physicists (which means there is only a slight increase of hope) and not for Novices.

Code legibility
:	as I (Justin Scholz, original author of the program) won't be at the working group of initial use for eternity, this program and especially the code must be understandable and comprehensible. This is not supposed to be a nice 6 month project that is never touched again.

Cross-platform
:	JUMP is written in Python 3, a language that is widely used in scientific programing, It uses the open-source library *PyVISA* to control the instruments and PyVISA relies on NationalInstruments drivers (for now. There is a new device layer the authors behind PyVISA are building for USB and GBIP). The way it currently is means that it runs on Windows (tested with Windows 10) and Linux (tested with Cent OS 7). Usual deployment currently involves installing Anaconda to provide the Python framework (for easier maintenance) but PyInstaller might provide an easier option to get it deployed faster to measurement PCs.

## Usability [Usability] ##

The goal of usability is very important as this program is aiming to replace the old, trusted, reliable (well, if a windows update is not popping you out of the windows command line full-screen, stopping the measurement) private qBasic predecessor. The also private LabView based predecessor made huge improvements by providing a user-facing GUI, better data analyzation and calculations.
JUMP right now is command-line only but one of the first further developments should be a live view of the data which should be as is rather easy to implement. Another tent-pole for better usability is to provide a way to pause measurements on the fly and change the tasks that are to be executed. Last but not least, a template system for quickly creating the tasks for standard measurement cases should be implemented to drastically further increase usability.

## Extensibility ##

This program was designed to provide a straight-forward and easy way to implement/add new hardware devices as measurement devices. This is critical for us as we sometimes get new devices and implementing them in the code base of its predecessor(s) is not a straight-forward approach. JUMP uses a single class for a hardware device that has a specified pre-defined structure and enforces it via Python language features (it's inheritance based). A simple template with all the needed methods is available and a good starting point as well as the already implemented examples of the ALPHA Analyzer and the LakeShore temperature controller 336 make a good starting point for adding new devices. Details on how to add new devices specifically are explained in the _[How To Change][HowToChange]_ section.

## Flexibility ##

Due to the design, there is a very clear distinction between controlling parameters and gathering actual measurement data. More on that in the [Concept][Concept] part. This provides added flexibility for more complex measurement experiments where multiple parameters at multiple devices need to be controlled and not necessarily measured with the same device.

This flexibility is extended to measurement setups (the physical measurement setups has its own set of limits and peculiarities which can be implemented using a nice template already existing.). Exports are currently not made as a module with flexibility but this may be a wise step for the future development of this program to modularize the export. 

## Code legibility ##

This ties in closely with the [Usability Aspect][Usability]. It is absolutely crucial that the code written here is understandable and easy. A lot of people who are __not__ professional programmers will be the ones to actually use, modify and extend this program. Therefore, very complex concepts are a no-go.

# Concept [Concept] #

This part aims to explain the main design concepts and ideas of the program so a user understands the (at least for us new) distincion between measurables and controlables, what this means for data post-processing and other peculiarity in data-processing.

## Measurables and Controllables ##

JUMP introduces/uses the concept of *Measurables* and *Controlables*. 

Controlable
:	Everything you can actively control is a controlable. In terms of dielectric measurements, it may be the excitation voltage or the applied frequency. It might also be the setpoint for the temperature for the temperature controller. A controlable can essentially be seen as a parameter with logic attached to it. It can then be changed in a controlled manner and different values for this change can be calculated or supplied.
:	_Paramater + How Should this parameter be changed at what events/time = Controlable_


Measurable
:	Essentially some result/value you can request and read out from your device. This means that in dielectric measurement terms, after the controlable of the applied frequency was set, one can trigger the measurable of "frequency-reponse" to measure the frequency-response with the previously specified parameters in device initialization and controlable setting.

*Note: Under some circumstances, the lines between controlables and measurables aren't very sharp. For example, you can set the controlable **setpoint** of the temperaure and read out/measure the measurable "sample temperature".*

__Birthing of Measurables and Controlables__

> _So how do Measurables and Controlables get into this world? Where do they come from?_
>> --- The User once asked

The general idea is that all communication towards the hardware should first go through the measurement setup as the setup may have limits a simple hardware implementation might be unaware of (A specific coldhead might only be allowed to go to 450K and not more whereas the temperature controller is capable of theoretically 1000 K in other setups). This consequently resulted in the decision to let the MeasurementSetup surface the Measurables And Controlables from connected hardware. Another very hands-on example is that the temperature controller is not aware of which sensor is "the sample sensor" in your setup. As a result, the measurement setup is a shim-layer that has the knowledge about whether Sensor A,B,C or D is the sample sensor. More on why and how, refer to the _[How To Change][HowToChange]_ section where a detailed design and conceptual overview of the packages and classes are provided.


## ParameterController, DataAcquisition and Trigger [ParamContr, DataAcq, Trigger]##

There is also the important concept of _ParameterControllers, DataAcquisitions and Triggers_. These are the currently supported types of tasks in the _[Task List][]_.

ParameterController (abbr: ParamContr)
:	Controls the Controlable. After setting each desired value, it runs all sub-tasks/child-tasks. A ParamContr can be set to two different modes currently.
- __ramp__
_Ramp_ is a mode designed primarily to be used with temperature controllers. It generates the behaviour of
_"Go from 300 K to 250 K with 0.4 K/min, triggering all sub_tasks every 1 K)"._ It uses a ramp to do that, implying that it freezes the setpoint when sub_tasks are executed but sets the new setpoint to where it _should_ be after the time it took for the measurement. This way, the overall resulting rate is guaranteed to match the desired one. 
- __specific values__
The _specific values_ mode is designed primarily to be used with frequency response measurements and alike. It receives a list of values (the user gets asked how you want to create/generate/modify this list) and then sets the associated controlable to the value of the list one at a time. So e.g. if the user wants to measure 30 logarithmicly distributed frequencies between 1 Hz and 10 MHz, a _specific values_ paramter controller is used. This parameter controller will utilize a logarithmical list of 30 values from 1->10,000,000. The paramContr will then set the associated controlable's value to each of the values in the list and starts every subtask sequentially after setting each new value.

DataAcquisition (abbr: DataAcq)
:	A kind of task which just asks the measurement device to deliver the current value for the Measurable and start all sub_tasks sequentially. As an added bonus, it can be set to output the max positive and negative deviation from the start value. (Its main measurable can be measured every x seconds continuesly while the sub_tasks are run). When you measure a very low frequency, e.g. 0.000001 Hertz, measuring a single point can take up to multiple days so it's good to know how much the temperature fluctuated in the meantime.

Trigger (abbr: Trigger) ```Not implemented fully yet!```
:	A kind of task that triggers sub_tasks when a specific condition is met. That means that for example a specific time is reached. This enables periods of constant temperature with continued regular measurements (for 5 hours, measure 3 minutes after the last one). Another possibility is, a specific measurable reaches a certain threshhold (eg when the humidity reaches 80%), start the sub_tasks.

## The Task List [Task List]##

The real measurement run is controlled by the task list. The task list is a hierarchical list that contains tasks (tasks are one of the 3 types described in the _[task-type-sections][ParamContr, DataAcq, Trigger]_) is processed in a step-into+sequential manner. If a task cas multiple steps (in the case of controlables), at every single step, this task's child-tasks are run sequentially (if these child tasks have child-tasks themselves, at every step, it will also run all the child tasks sequentially going as deep as wanted). It is a tree-like structure where execution starts at the root and node one level deeper is executed and each node itself may execute sub_nodes sequentially.

An example task list looks like this:

```
[0] ParamContr: T_Setpoint: 300K to 250K with 5 K/min and measure every 3 K
	[0,0] DataAcqu: Sample Sensor temperature, averaging through sub_task
		[0,0,0] ParamContr: Applied_freq at ALPHA from 1 Hz to 1e7 Hz log, 30 freq
			[0,0,0,0] DataAcq: RX response at ALPHA
[1] ParamContr: T_Setpoint: 250K to 300K with 5 K/min and measure every 3 K
	[1,0] DataAcqu: Sample Sensor temperature, averaging through sub_task
	[1,1] ParamContr: Applied_freq at ALPHA from 1 Hz to 1e7 Hz log, 30 freq
		[1,1,0] DataAcq: RX response at ALPHA
```


## Workflow [Workflow] ##

The main workflow can currently be separated into three major phases.

<div style="text-align:center">
![][3 Phases]
<figcaption>3 main phases of a JUMP Workflow</figcaption>
</div>

[3 Phases]: 
./Documentation_sources/3-phases.png "3 Phases"  width=400px

__1. Phase:__ General data, device initialization as well as task list setup.
In this phase, the user enters his name, the name of the measurement and general info alike. He/She then proceeds to choose the measurement setup, the used devices and most importantly sets up the _[task list][Task List]_.

__2. Phase:__ The measurement phase
The task list is executed the following way: Task [0] gets started. The temperature setpoint will be continuesly until it reaches a threshhold of 3 K. At the beginning of the task, all sub_tasks that are exactly one level below the task are started. After this first trigger, every 3 K the temeprature won't be set continuesly until all sub_tasks that are exactly one level deeper have finished. The speed of the temperature setpoint's changing is 5 K/min.
Task [0,0], being exactly one level deeper below will be started the second time when the setpoint surpassed the 297 K threshold. The current sample temperature will be read out and saved in the in-memory database. After having read out the sample temperature, the sub_task [0,0,0] will be started. A specific frequency will be set at the ALPHA anaylzer. After that, the sub_task [0,0,0,0] will be started, which gatheres the measurement data from the ALPHA analyzer.
As [0,0] is configured to "average through sub_task", it will run continuesly and read out the sample temperature during the execution of [0,0,0] and [0,0,0,0]. This means that the end result will be the start_value, the maximum positive deviation and the maximum negative deviation from this value throughout the time it took to perform [0,0,0] and [0,0,0,0].

The task [1] is analogous to the [0] task. Task [1,0] is also analogous to [0,0], without any sub_takss, though. So the sample temperature will be measured and saved and then all the frequency responses will be measured.


__3. Phase:__ Data processing and export
In phase 3, the user merges,combines and inverts the data in a meaningful way. A future programing effort to make a template for dielectric measurements seems wise but is not in the scope of the current endevour. 

Usually, one has two essential steps for data post-processing and making it ready for export:

Merging
:	One merges the parent paramContr. with the sub_DataAcqu. This step ensures that to each datapoint gathered, there are specific parameters in the data. An RX datapoint isn't so useful if you don't know what frequency it represents. Also, a temperature setpoint is helpful for comparing it to the actually measured temperature. This is done by merging. This is a 1-1 process of linking the first item in the parent with the first in the sub_task specified.

Integrating
:	In the integrating step, one combines two (usually paramContr) tasks together. In the above example, the temperature run should be combined in such a way that every frequency and RX datapoint is linked to a specific temperature. This is a 1-n linking, so the temperature ramp has 1 specific temperature at a time but eg 30 frequencies associated with that temperature.

To understand this better, let's discuss a sample database of a single sweep:

`````
[0]: [{setpoint_freq: 10}, {setpoint frequency: 20}, {setpoint frequency 50}]
[0,0]: [{R:1, X:2, dev_freq: 10}, {R:5, X:10, dev_freq: 10}, {R:20, X:50, dev_freq: 10}]
`````

It is obvious that in `[0]` as well as in `[0,0]`, there are __3__ datapackages. One could boil it down to a display of:

```
[0]: 3 items
[0,0]: 3 items
```

What we really want is something like:

`````
[0]: [{setpoint_freq: 10, R:1, X:2, dev_freq: 10},
	{setpoint frequency: 20, R:5, X:10, dev_freq: 10},
	{setpoint frequency: 50, R:20, X:50, dev_freq: 10}]

`````

That is a merge where both lists of datapackages have the same number of datapackes in them. It's a 1-1 mapping, essentially going through the first item of [0] and appending the first item of `[0,0]`, then taking the second item of `[0]` and appending the second item in `[0,0]` and so on and so forth. In the practical workflow, there is only the further differentiation between *same-level merges* and *different-level merges*, the only difference being the identifiers. 

Same-level-merges
:	A *same-level-merge* is across the same level-depth in the tree. Merging `[0]` and `[1]`, `[1,0]` and `[1,3]` or `[1,0]` and `[1,1]`.

Different-level-merges
:	A *different-level-merge* is across 1 level. So eg `[0]` and `[0,0]`, `[1]` and `[1,0]` or `[0,1]` and `[0,1,0]`.

In case of more classical dieletric measurements, there will most likely be four lists of datapackages for one temperature ramp. Eg:

`````
[0]: Setpoint Ramp (100 K -> 200 K every 5 K) => 21 setpoint values
[0,0]: Sample Sensor temp => 21 datapackages (sample_temp, max_pos_deviation, max_negative_deviation)
[0,0,0]: Applied frequency list to measurement device 30 frequencies => 30*21=630 datapackages
[0,0,0,0]: Measured frequency response => 30*21=630 datapackages
`````

Data is written sequentially into the database. This results in a scenario where only 21 datapackages for the `[0]` and `[0,0]` tasks and 630 datapackages in the lists for [0,0,0] and `[0,0,0,0]` exist. __But__ it is clear that the first 30 datapackages of `[0,0,0,0]` belong to the very first item of `[0]` (there are 30 frequencies for 1 temperature the way it was set up). Which leads to the process of *integrating_datarows*.

Integration
:	Using an x -> x*n relation, putting the correct n values inside each element of the parent. 

To sum it up, the full processing of the example introduced above would be:
- merge `[0]` and `[0,0]` 
- merge `[0,0,0]` with `[0,0,0,0]` 
- integrate `[0,0,0]` into `[0]`.

_The result is that every datapackage of [0] contains the sample temperature (because of the same-level merge) and also has 30 datapackages (applied_freq+measured response due to same-level merge) associated (due to the integration step). With this at hand, we can easily generate 1 file per temperature and put the 30 indiviual frequency datapoints into it. Transposing the data is automatically done (having 1 file per frequency) if the user so choses._

# How to Change or Extend this program [HowToChange] #

## General programing basic knowledge required for this program ##

### Object oriented programing ###

> Previously, there was only sequential programing. Now it may be with objects, too!
>> --- The User

Object oriented programing is a different way of programing than classical functional or sequential programing.
In the classical way of programing, one usually defines functions to write code once, but state is passed around and globally kept (meaning variables are NOT directly associated with the ways you can manipulate the variables/data).

In contrast, *object oriented programing (OOP)* introduced the concept of so called "classes" and "objects" to the world of programing.

One can look at a *class* to be something like a model for an object. There can be many objects of one class.

__Example:__ Imagine a form for students for a method course. Every student will have to provide specific information when he signs up for the course. He will likely provide: 

- name
- surname
- semester

In OOP, the class "Student" then has the attributes *name, surname, semester*. Additionally, the teacher can either allow or deny every student the attendance to the course. Every student can be denied or allowed. So the class "Student" would have the method 

- Allow/Deny Attendance

Now every student will be an *object* of the class *Student*. This means that for three students, you will look into your class, ask each student for his/her name, surname and semester. When the object is created (the students data is integrated into the system), each student'S the "Allow/Deny Attendance" method can be invoked.

Looking at the student Nicolai Tesla who is in his 3rd semester, the object will be:

`````
object1 (of class "Student")
name: Nicolai
surname: Tesla
semester: 3

method "allow/deny attendance"()
`````

> **Objects** are like containers for information that is related closely to itself.
**Objects** also contain methods to manipulate the data they store.
>> --- The User

__Example 2 (about friends):__

If I were to ask you to name me your friends, you would most likely **NOT** do something like this:

list 1:

- Elon
- Nicolai
- Steve

list 2:

- Musk
- Nicolson
- Tesla

instead, you would say something like:

- Nicolai Tesla
- Steve Nicolson
- Elon Musk

You know that a friend has a first name and a last name and there is a relation. The first first name is combined with the first surname. You have the class "friend" and it contains two variables, *first name* and *sur name*. 

### Inheritance ###

Inheritance means, like the word implies, inheriting something else's properties. In the previous example, a "human" class that contains fields for "first name" and "sur name". One could then easily create the "student" class merely by saying that "*it's the human class and add the field __semester__ *". In our specific case, this is used extensively to manage the hardware-device classses. There is a _MeasurementDevice_ class that defines what the general idea of a MeasurementDevice is and then many child-classes, one for each device that may implement private methods (see private/public section in _[Python bits and bobs][PythonBitsAndBobs]_) to accommodate the specific quirks of the devices. In our case, the MeasurementDevice is an _abstract_ class meaning that it itself will never be used to make an object but only as a model for other classes.

### Threads ###

Let's assume the following:
A measurement of the frequency response for 1*10^-3 Hz should be performed. It will take a very long time. Ideally, you would like to have continued data of some sort for the temperature throughout the long measurement. This is what is achieved by Threads. Threads can run in parallel and completely separate from the main program flow.

<div style="text-align:center">
![Threads][Threads]
<figcaption>Threads. **"Do more stuff"** and **"Do 2nd stuff"** run in parallel.</figcaption>
</div>

[Threads]: 
./Documentation_sources/Threads.png "Threads"  width=600px

The red box around __Do more stuff__ and __Do 2nd stuff__ marks the parallel execution of both. In a truly parallel fashion, you can measure both temperature again and again even though at the same time, a measurement of the frequency response is running.

In JUMP, there are potentially a lot of Threads. Most of them are the Threads of the Tasks. Every task is its own Thread.

> Threads are like getting new people employed so you can work in parallel. You have slightly more work to manage and coordinate them, though.
>> --- The User

### Python bits and bobs [PythonBitsAndBobs]###

__Private and public methods__

Methods can be private and public. In Python, this is more strong advice than it is enforced in the compiler. Code editors with assisted typing won't show private methods in auto-completion. A public method is something that anyone externally will be able to call and where it's the design's idea that it is called from some other object.
Contrasting to that, a __private__ method is one that should only ever be called from within the object. Eg, the *ALPHA* Analyzer class, which inherited all methods and variables from the *MeasurementDevice* has its own methods to work with ALPHA specific answers and commands. But no object from outside should ever call a "_parse_ALPHA_results"-method, as it is not documented and not sure what data needs to go in there.

Private methods start with an \_ (underscore) in the name to indicate they are considered private. Being private in turn gives the coder the flexibility to rename, remove and introduce private methods as is desired as these ones are contained inside the class and the rest of the program *shouldn't* be at all affected when they are changed.

__Python *for* loops__

In Python, *for* loops work differently than in classic loops. Classically, a loop looks like:

`````
for (int it = 0, i < 3, i++)
	do something with i
end
`````

Python solves looping differently, usually trying to give the element itself rather than counting up an index. E.g.:

`````Python
list = ["yellow", "green", "blue"]
`````

Usually, *each element* is to be processed. Printing every item of the list would be:

`````Python
for color in list:
	print(color)
end
`````

This loop does nothing else then assign "yellow" to "color" so when the block to "print(color)" is called, "yellow" gets printed. Important to understand is that *color* in this case is **just a name**. It would also work as:

`````Python
for anvil in list:
	print(anvil)
end
`````

Say for some reason you really need the index? Python also provides a nifty method to modify the list for this matter:

`````Python
for index, item in enumerate(list):
	print("item #" + index + ": " + item)
end
`````

result would be:

`````
"item #0: yellow"
"item #1: green"
"item #2: blue"
`````

Again, *index* and *item* are just names, but it was shown how a current element inside the for block can be selected.

__Python packages__

In Python, Packages can be used to group classes together. In JUMP, the packages are named as indicated in the diagram of the "Structural Overview" section. 


## Structural overview ##

<div style="text-align:center">
![Test][Structural Overview]
<figcaption>Structural Overview</figcaption>
</div>

[Structural Overview]: 
./Documentation_sources/Structural_Overview.png "Structural Overview" width=600px

The general structure is made this way to achieve the goals.

### UserInput.py [UserInput] ###

The UserInput class is one unified class, every aspect of the program can leverage to either inform the user about something or ask the user what he desires to do. This means that currently, the Measurement_device object itself will send questions to the user by calling methods from UserInput. To program a full-fledged GUI for this program, UserInput.py is an appropriate starting point.

_What can be changed here?_

- The general question style. Templates are used throughout JUMP and here is the place to change how the template is formatted.

### MeasurementProgram.py [MeasurementProgram] ###

This is top-most layer of the program. MeasurementProgram.py classes have to guide the user through the 3 phases outlined above in the _[Workflow][]_ section. The only components it interacts with and has direct knowledge about are ones surfaced to it from the _DataStorage_ package and the _MeasurementComponents_. 

_What can be changed here?_

- Main program flow
- Interaction during measurement (e.g. provide a way to pause and change the task list during measurement)

### DataStorage.py [DataStorage] ###

This contains the storage class for the way data is stored from the tasks and also contains the mathematics module to calculate all values from measurement device data. For example an ALPHA analyzer provides R, X and freq, enabling the calculation of C and G and other quantities from that.

_What can be changed here?_

- Data manipulation
	- Provide a templating system to make data processing for standard dielectric measurements faster
- specifics of the format and structure of output files

### MeasurementComponents.py [MeasurementComponents] ###

This package contains the classes for _Trigger_, _DataAcquisition_, _ParameterController_ and _Measurement_. The Measurement-class organizes all the other ones. These are supposed to be the classes needed to get _Phase 2: Measuring_ working.

_What can be changed here?_

- Behaviour of ParameterController, DataAcquisition and Trigger
	- e.g. extending the ParameterController by another way to control values in a linear fashion. Currently, it uses the mentioned ramping method so that the final result will have an overall guaranteed changing rate.
- New task types


### MeasurementSetup.py [MeasurementSetup] ###

The place for all the MeasurementSetups (usually an oven or a coldhead with local limits and peculiarity). For example all the PID values for temperature controllers are here. The MeasurementSetup will impose the limits on values when measuring (one doesn't want to set the Temperature to 900 K in a coldhead that wouldn't survive this).

Furthermore, the MeasurementSetup defines what kind of devices are present. Eg a coldhead setup defines there to be a temperature controller and a measurement device. As the measurement setup is aware of the temperature controller being a temperature controller, it can send necessary PID adjustements corresponding to the specific temperatures to it. It will also provide the shim-layer to match between the user's "Sample temperature" and "control temperature" sensors and the hardware Sensors of the temperature controller.

Every Measurable and Controlable will be handled through the MeasurementSetup. This is due to the fact that additional information might be needed when crossing threshholds at the MeasurementSetup (e.g. PIDs might have to be changed).

_What can be changed here?_

- Implement a shiny new measurement setup. The DUMMY class is a straight-forward template. Duplicate it, rename it and implement the names, devices logic and begin measuring. __Important__: When duplicating the DUMMY class, make sure to include your own class'es name in the "MeasurementSetupHelper" Header.


### MeasurementHardware.py [MeasurementHardware] ###

The individual classes for measurement hardware like a LakeShore 336 temperature controller or a Novocontrol ALPHA analyzer. It will provide Measurables and Controlables in a standard way (for reference, look at the local DUMMY measurement device).

_What can be changed here?_

- New hardware can be implemented. To do this, it's easiest to duplicate the DUMMY class, rename it and implement the device specifics (and don't forget to put the name of your class inside the header of the MeasurementDeviceChooserHelper).
- Change device initialization

If you want to add a new hardware, you should first fire up PyCharm. Go into interactive python shell and run, one line after the other (each confirmed with enter):

`````Python
import visa
rm = visa.ResourceManager()
rm.list_resources()

`````

which will output the devices. Assuming the device is connectded at ```GPIB0::12::INSTR```, you continue with:

`````Python
inst = rm.open_resource('GPIB0::12::INSTR')
print(inst.query("*IDN?"))

`````

This will yield the IDN value that is used to determine what devices are present and therefore is needed to implement a new device.

## Loose Ends ##

This section describes what is currently missing.

### Abort options throughout measurement ###

Some sort of graceful "cancel current measurement and restart" or something like that should probably be implemented. Currently, Threads can crash and the whole program can go down with it.

### Live data display ###

Due to the availability of the DataBase as a simple object that one can poll, it should be fairly straight-forward to provide a live graph of at least every task via matplotlip and tkinter (both python packages).

## Tools ##

One last word about tools from the User:

> Use good tools. When going into the code, use an IDE like PyCharm to load and open the program.
>> --- The User


# Credits

All of the chair of experimental phyiscs V at the University of Augbsurg where I was able to work on this project and had constant, valuable and constructive feedback about it.

_Special thanks go to **Pit Sippel** for providing me guidance for the general structure of this program_ and **Dr. Stephan Krohns** who supervised and allowed me to take on this project. Also a big "thank you" to Tron for inspiring me to write from the perspective of _The User_.