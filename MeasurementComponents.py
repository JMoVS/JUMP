"""This module packages up the MeasurementController class to control the measuring hardware on an abstract level as
well as the Measurement class which takes out and implements the actual measuring process"""
__copyright__ = "Copyright 2015 - 2017, Justin Scholz"
__author__ = "Justin Scholz"

import queue
from threading import Thread
from abc import ABCMeta, abstractmethod
import math
import time

from MeasurementSetups import MeasurementSetup
import MeasurementSetups
import UserInput
from DataStorage import main_db


class Task(metaclass=ABCMeta):
    @abstractmethod
    def do(self):
        pass

    @abstractmethod
    def generate_one_line_summary(self):
        pass


class Trigger(Thread, Task):
    """Class that provides functionality for triggering a sub task on a time or measurable base
    """

    def __init__(self, identifier: [], measurement_setup: MeasurementSetup, trigger: dict, global_task_list: []):
        """
        :param identifier:
        :param measurement_setup:
        :param trigger: {"total_time_span": 300, "trigger_separation": 3} or
        {"acquis_triggering_measurable": measurable_dict, "acquis_triggering_value": 200}
        :param global_task_list:
        """
        super().__init__()
        self.should_do_now = False
        self.should_be_running = True
        self.global_task_list = global_task_list
        self.trigger = trigger
        self.measurement_setup = measurement_setup
        self.identifier = identifier
        self.mode = None  # type: str
        self.total_time_span = None
        self.trigger_separation = None
        self.acquis_triggering_measurable = None
        self.acquis_triggering_value = None
        if "total_time_span" in trigger:
            self.total_time_span = float(trigger["total_time_span"])
            self.trigger_separation = trigger["trigger_separation"]
            self.mode = "time"
        elif "acquis_triggering_measurable" in trigger:
            self.acquis_triggering_measurable = trigger["acquis_triggering_measurable"]
            self.acquis_triggering_value = trigger["acquis_triggering_value"]
            self.trigger_when_below = trigger["trigger_when_below"]
            self.mode = "measurable"
        main_db.make_storage(identifier, "Trigger", self.generate_one_line_summary())

    def run(self):
        while self.should_be_running:
            if self.should_do_now:
                self.do()
                self.should_do_now = False
            time.sleep(0.05)

    def do(self):
        if self.mode == "time":
            self._time_based_triggering()
        elif self.mode == "measurable":
            self._measurable_value_based_triggering()

    def _time_based_triggering(self):
        sub_tasks = Helper.check_for_sub_tasks(self.identifier, self.global_task_list)

        start_time = time.perf_counter()
        end_time = start_time + (self.total_time_span * 60.0)

        next_trigger_time = start_time

        UserInput.post_status("{0}: Started Trigger task '{1}'.".format(time.strftime("%c"), str(self.name)))

        # Only while the end time isn't reached
        while end_time > time.perf_counter():
            # check for next trigger time. If it is time to trigger, then run all direct_sub_tasks after each other
            if time.perf_counter() > next_trigger_time:
                datapackage_start_time = time.strftime("%H %M %S")
                for task in sub_tasks:
                    task.should_do_now = True
                    while task.should_do_now:
                        pass
                    UserInput.post_status(time.strftime("%c") + ": Waiting for new trigger time to be reached.")
                datapackage_end_time = time.strftime("%H %M %S")
                datapoint = {"start_time": datapackage_start_time, "end_time": datapackage_end_time}
                main_db.add_point(self.identifier, datapoint)

                # we only calculate the time of when to trigger next if we reached the previous one!
                next_trigger_time = time.perf_counter() + self.trigger_separation * 60

        return

    def _measurable_value_based_triggering(self):  # TODO: One could think of optionally implementing a time out
        # TODO: Implement measurable triggered code path. Problem to solve is: how does the user select which one of the
        # potentially many values inside a datapoint (look at ALPHA - it's R,X and freq) to use for comparison
        UserInput.confirm_warning("Not implemented yet!!")
        pass

    def generate_one_line_summary(self):
        if self.mode == "time":
            summary = "Total time is {0} minutes. Firing off sub_taks every {1} minutes.".format(
                str(self.total_time_span), str(self.trigger_separation))

        else:
            summary = "meh, doesn't work with measurables yet!"
        return summary


class DataAcquisition(Thread, Task):
    """This class is for an individual _acquire_point, so multiple frequencies are measured"""

    def __init__(self, identifier: [],
                 measurement_setup: MeasurementSetup, measurable: dict,
                 average_through_sub_controlable: bool, global_task_list: []):
        """initializes the measurement object with a frequency list (remember, this is essentially a single _acquire_point!)
        and the measurementDeviceController so it can actually start the measurement on device. Should later be
        initialized with a temp device controller optionally
        :type identifier: []
        :type measurable: dict
        :param measurable: A dictionary created by a measurement setup
        :param measurement_setup:
        :return: """

        super().__init__()
        self.should_do_now = False
        self.should_be_running = True
        self.global_task_list = global_task_list
        self.identifier = identifier
        self.average_through_sub_task = average_through_sub_controlable
        self.measurable = measurable
        self.measurement_setup = measurement_setup
        self.sub_tasks = []
        main_db.make_storage(identifier, "DataAcq", self.generate_one_line_summary())

        return

    def generate_one_line_summary(self):
        """
        :returns One-line summary
        :rtype: str
        """

        text = "Acquires data from" + self.measurable["dev"].name
        text += " and is "
        if self.average_through_sub_task:
            average = ""
        else:
            average = "no "

        summary = text + average + "averaging datapoints while sub_tasks are run."

        return summary

    def run(self):
        while self.should_be_running:
            if self.should_do_now:
                self.do()
                self.should_do_now = False
        time.sleep(0.01)

    def acquire_point(self):
        """This method performs a sweep with the measurables stored in the DataAcquisition objects frequ_list variable (set
        during initialization, will probably be calls as a thread to not have to wait for the
        """

        if not self.has_sub_tasks:  # This means we can eg just pass a measuring command to a device and
            # acquire data instead of having to make sure that a specific condition eg a temperature is reached

            datapoint = self.measurement_setup.measure_measurable(self.measurable)
            main_db.add_point(self.identifier, datapoint)

        elif self.has_sub_tasks:  # if we have a task
            start_datapackage = self.measurement_setup.measure_measurable(self.measurable)  # type: dict

            # initialize the averaging logic if needed
            if self.average_through_sub_task:
                max_negative_deviation_datapackage = start_datapackage.copy()
                max_positive_deviation_datapackage = start_datapackage.copy()
                average_datapackage = start_datapackage.copy()
                averager = 1  # the variable used to calculate the true average

            for task in self.sub_tasks:  # execute every sub_task
                task.should_do_now = True
                if self.average_through_sub_task:
                    while task.should_do_now:
                        # we need the current datapackage
                        current_datapoint = self.measurement_setup.measure_measurable(self.measurable)  # type: dict

                        # if needed refresh the max_negative deviation
                        for key in max_negative_deviation_datapackage.keys():
                            # if it's the time key, it's a str, we can't really calculate with strings
                            if type(max_negative_deviation_datapackage[key]) == float:

                                # If the currently maximum negative deviation is bigger than the current value, it's
                                # not the maximum so it's rewritten
                                if max_negative_deviation_datapackage[key] > current_datapoint[key]:
                                    max_negative_deviation_datapackage[key] = current_datapoint[key]

                        # if needed refresh the max_positive deviation
                        for key in max_positive_deviation_datapackage.keys():
                            if type(max_negative_deviation_datapackage[key]) == float:
                                # If the currently maximum positive deviation is bigger than the current value, it's
                                # not the maximum so it's rewritten
                                if max_positive_deviation_datapackage[key] < current_datapoint[key]:
                                    max_positive_deviation_datapackage[key] = current_datapoint[key]

                        # calculate the current average throughout the whole thingy
                        for key in average_datapackage.keys():
                            if type(average_datapackage[key]) == float:
                                current_average = average_datapackage[key]
                                expanded_average = current_average * averager
                                expanded_average += current_datapoint[key]
                                new_average = expanded_average / (averager + 1)
                                average_datapackage[key] = new_average
                                averager += 1

                        # Make points every 1 seconds. If you want that to be a setting, include in the
                        # acquisition Class as a parameter, eg "averaging point frequency
                        time.sleep(5)

                while task.should_do_now:
                    pass

            if self.average_through_sub_task:
                final_max_negative_deviation_datapackage = {}
                # now append all the relevant postfixes:
                for key in max_negative_deviation_datapackage.keys():
                    if type(max_negative_deviation_datapackage[key]) == float:
                        new_key = key + "_max_-"
                        # we set the new suffixed key to the then removed item at place key. Essentially renaming the
                        # key
                        final_max_negative_deviation_datapackage[new_key] = max_negative_deviation_datapackage[key]

                final_max_positive_deviation_datapackage = {}
                for key in max_positive_deviation_datapackage.keys():
                    if type(max_positive_deviation_datapackage[key]) == float:
                        new_key = key + "_max_+"
                        # we set the new suffixed key to the then removed item at place key. Essentially renaming the
                        # key
                        final_max_positive_deviation_datapackage[new_key] = max_positive_deviation_datapackage[key]

                final_average_datapackage = {}
                for key in average_datapackage.keys():
                    if type(average_datapackage[key]) == float:
                        new_key = key + "_aver"
                        # we set the new suffixed key to the then removed item at place key. Essentially renaming the
                        # key
                        final_average_datapackage[new_key] = average_datapackage[key]

                # Now update the starting_point dict with the now calculated thingies
                start_datapackage.update(final_max_negative_deviation_datapackage)
                start_datapackage.update(final_max_positive_deviation_datapackage)
                start_datapackage.update(final_average_datapackage)

            # And in every case add the starting data package to the thingy

            main_db.add_point(self.identifier, start_datapackage)

        return

    def do(self):
        self.sub_tasks = Helper.check_for_sub_tasks(self.identifier, self.global_task_list)
        if len(self.sub_tasks) == 0:
            self.has_sub_tasks = False
        else:
            self.has_sub_tasks = True
        self.acquire_point()


class ParameterController(Thread, Task):
    """
    Objects will be Threads that control a controlable, eg the temperature and use classic ramping in currently the
    ramping method layout in the README to trigger a sweep at specific points. If one wanted to implement different ramping of
    a controlable (eg temperature, moisture or something), one could introduce a new switch and then implement the ramp
    here.
    """

    def __init__(self, identifier: [], measurement_setup: MeasurementSetup, meas_setup_controlable,
                 trigger: {}, global_task_list: []):
        """
        :type identifier: [int]
        :param controlable: A dictionary created by the meas_setup to specify device and controlable
        :param trigger_separation: when we want to measure every 3 K, we need to trigger every 3 K. So value would be 3
        :param measurement_setup: that's the ms for the controlable we are talking about
        :param start_value: eg starting temperature (200K)
        :param rate_for_controllable: eg 0.15 [K]
        :param end_value: eg end temperature (300)
        """

        # acquis_triggering_measurable, start_value, rate_for_controllable, end_value,
        #         trigger_separation, specific_values: [])

        super().__init__()
        self.should_be_running = True
        self.should_do_now = False
        self.global_task_list = global_task_list
        self.sub_tasks = []
        self.identifier = identifier
        self.meas_setup_controlable = meas_setup_controlable
        self.ms = measurement_setup
        self.mode = None
        self.all_values_reached = False
        if "start_value" in trigger:
            self.start_value = trigger["start_value"]
            self.trigger_separation = trigger["trigger_separation"]
            self.rate_for_controllable = trigger["rate_for_controlable"]
            self.milisecond_rate = self.rate_for_controllable / (60)  # minutes and seconds ->miliseconds
            self.end_value = trigger["end_value"]
            self.end_value_reached_when_below = None  # type: bool # whether ramp goes up or down
            if self.end_value > self.start_value:
                self.end_value_reached_when_below = False
            else:
                self.end_value_reached_when_below = True
            self.mode = "ramp"
        elif "specific_values" in trigger:
            self.specific_values = trigger["specific_values"]
            self.mode = "spec_values"

        main_db.make_storage(self.identifier, "ParamContr", self.generate_one_line_summary())

    def generate_one_line_summary(self):
        """
        :returns Oneline summary
        :rtype: str
        """
        text = self.mode + " :"
        dev_name = self.meas_setup_controlable["dev"].name + " "
        controled_param = self.meas_setup_controlable["name"] + " "
        summary = ""

        if self.mode == "ramp":
            summary = str(text) + str(dev_name) + str(controled_param) + "from " + str(self.start_value) + " to " + \
                      str(self.end_value) + " triggering every " + str(self.trigger_separation) + \
                      " and controlling at a rate of " + str(self.rate_for_controllable) + "."
        elif self.mode == "spec_values":
            summary = str(text) + str(dev_name) + str(
                controled_param) + "setting specified values and triggering sub_tasks then"
        return summary

    def run(self):
        """starts a thread of ParameterController when called by calling "start" (!! don't call "run"!)

        :return:
        """

        while self.should_be_running:
            if self.should_do_now:
                self.do()
                self.should_do_now = False
            time.sleep(0.01)

        return

    def _start_and_stop_sub_tasks(self):
        # self.sub´_tasks gets updates when the Thread is started with the run method
        for task in self.sub_tasks:
            # start the action on the thread. If the property "should_do_now" is changed to False again, it is finished
            task.should_do_now = True
            while task.should_do_now:
                pass

    def do(self):
        self.sub_tasks = Helper.check_for_sub_tasks(self.identifier, self.global_task_list)

        if self.mode == "ramp": 
            start_time = time.perf_counter()
            current_value = self.start_value
            most_recent_value = self.start_value

            # The very first temperature should also be sweepin'
            datapoint = self.ms.change_value_of_controlable_to(self.meas_setup_controlable, current_value)
            main_db.add_point(self.identifier, datapoint)
            self._start_and_stop_sub_tasks()

            while not self.all_values_reached:
                sweeped_this_cycle = False
                # when we get the relative time to the start of this controllable, we can calculate our expected setpoint
                # according to the rate specified, therefore we first gather the current time
                current_relative_time = (time.perf_counter() - start_time)  # some float in milliseconds

                # new setpoint value is start value * relative time in milliseconds * millisecond_rate as this is a linear
                # function and we want to use the mentioned ramping method.
                if self.end_value_reached_when_below:
                    setpoint_value = self.start_value - current_relative_time * self.milisecond_rate
                    if setpoint_value < self.end_value:
                        setpoint_value = self.end_value
                else:
                    setpoint_value = self.start_value + current_relative_time * self.milisecond_rate
                    if setpoint_value > self.end_value:
                        setpoint_value = self.end_value

                UserInput.post_status(time.strftime("%c") + ": Halting " + self.generate_one_line_summary())
                # Actually send the temperature controller a new value
                datapoint = self.ms.change_value_of_controlable_to(self.meas_setup_controlable, setpoint_value)

                current_value = setpoint_value

                # This is the if condition to trigger sub_tasks
                if abs(current_value - most_recent_value) >= self.trigger_separation:
                    most_recent_value = current_value

                    # we only add a datapoint if we are triggering sub_tasks:
                    main_db.add_point(self.identifier, datapoint)
                    self._start_and_stop_sub_tasks()
                    sweeped_this_cycle = True

                UserInput.post_status(time.strftime("%c") + ": Resuming: " + self.generate_one_line_summary())

                if self.end_value_reached_when_below:
                    if current_value <= self.end_value:
                        self.all_values_reached = True
                        # and we sweep when we reach the final value, but only if we didn't already sweep
                        if not sweeped_this_cycle:
                            main_db.add_point(self.identifier, datapoint)
                            self._start_and_stop_sub_tasks()
                            UserInput.post_status(time.strftime("%c") + ": Ramp " + self.generate_one_line_summary() + " now done!")
                elif not self.end_value_reached_when_below:
                    if current_value >= self.end_value:
                        self.all_values_reached = True
                        # and we sweep when we reach the final value, but only if we didn't already sweep
                        if not sweeped_this_cycle:
                            UserInput.post_status(time.strftime("%c") + ": Ramp " + self.generate_one_line_summary() + " now done!")
                            main_db.add_point(self.identifier, datapoint)
                            self._start_and_stop_sub_tasks()

                # TODO: Do we need to introduce a time out/sleep because we are setting temperatures to quickly?
                time.sleep(0.01)

        elif self.mode == "spec_values":
            UserInput.post_status(time.strftime("%c") + ": Started " + self.generate_one_line_summary())
            for specific_controlable_value in self.specific_values:
                datapoint = self.ms.change_value_of_controlable_to(self.meas_setup_controlable,
                                                                   specific_controlable_value)
                main_db.add_point(self.identifier, datapoint)
                self._start_and_stop_sub_tasks()


class Measurement:
    """This class has all the relevant info for one Measurement step (eg from 10 to 300 K _acquire_point every 3 seconds the
        frequencies x,y,z
        """

    def __init__(self):
        self.tasks = []  # type: [Task]
        self.task_input = [] #User input to questions. Variable helps with setting up a new template
        self.meas_setup = None  # type: MeasurementSetups.MeasurementSetup
        self._choose_meas_setup()
        self.meas_setup.init_after_creation()
        return

    def _choose_meas_setup(self):
        self.meas_setup_chooser = MeasurementSetups.MeasurementSetupHelper()
        self.list_of_setups = self.meas_setup_chooser.list_available_setups()
        question = {"question_title": "Measurement Setup",
                    "question_text": "Please choose your current measurement setup",
                    "default_answer": 0,
                    "optiontype": "multi_choice", "valid_options": self.list_of_setups}
        answer = UserInput.ask_user_for_input(question)["answer"]

        self.meas_setup = self.meas_setup_chooser.select_setup(self.list_of_setups[answer])

    def new_task(self,custom_type=True,template=[]):
        # We need measurement setup controlables and measurables
        template=template
        available_raw_controlables = self.meas_setup.get_controlables()
        available_controlables = []  # mainly used to be human readable in questions
        for controlable in available_raw_controlables:
            text_option = controlable["name"] + " at device: " + controlable["dev"].name
            available_controlables.append(text_option)
        available_raw_measurables = self.meas_setup.get_measurables()
        available_measurables = []  # mainly used to be human readable in questions
        for meausurable in available_raw_measurables:
            text_option = meausurable["name"] + " at device: " + meausurable["dev"].name
            available_measurables.append(text_option)

        question = {"question_title": "Kind of task",
                    "question_text": "Do you want to create a Parameter Controller or a Data Acquisition or a Trigger?",
                    "default_answer": 0,
                    "optiontype": "multi_choice",
                    "valid_options": ["Parameter Controller", "Data Acquisition", "Trigger"]}
        answer = self._get_input(custom_type,question,template)

        # 0 = ParameterController, code path to create a new parameter controller
        if answer["answer"] == 0:
            param_controller = None

            question = {"question_title": "Choosing the controlable",
                        "question_text": "Which Controlable of the following available ones do you want to use? "
                                         "(Irrelevant if you want to use a time-triggered parameter controller",
                        "default_answer": 0,
                        "optiontype": "multi_choice",
                        "valid_options": available_controlables}
            answer = self._get_input(custom_type,question,template)
            desired_controlable = available_raw_controlables[answer["answer"]]
            UserInput.post_status("Beware of the following limits on this measurement setup!")
            limits = self.meas_setup.get_limits()
            for limit in limits:
                UserInput.post_status(limit)

            # We have four kinds of ParamControllers: ramp-based, specific values, measurable- and time-triggered
            question = {"question_title": "ParamController type",
                        "question_text": "Do you want to create a ramp-based, specific values, measurable-triggered or"
                                         " time triggered controller?",
                        "default_answer": 0,
                        "optiontype": "multi_choice",
                        "valid_options": ["ramp-based (eg temperature)",
                                          "specific values (eg frequencies)"]}
            answer = self._get_input(custom_type,question,template)

            # answer being 0 means ramp-based is wanted
            if answer["answer"] == 0:

                # Get a start value for the controlable
                # TODO: One could think of imposing more sensible limits on the controlable here
                question = {"question_title": "Start Value for " + desired_controlable["name"],
                            "question_text": "What is the desired start value?",
                            "default_answer": 300,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1e64,
                            "valid_options_steplength": 1e1}
                answer = self._get_input(custom_type,question,template)
                start_value = answer["answer"]

                question = {"question_title": "End Value",
                            "question_text": "What is the end value?",
                            "default_answer": 20,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1000.0,
                            "valid_options_steplength": 1e1}
                answer = self._get_input(custom_type,question,template)
                end_value = answer["answer"]

                # trigger spearation is how often the inner part of the task list should be triggered
                question = {"question_title": "Trigger separation ",
                            "question_text": "What shall be the interval after which a sub_task is triggered? "
                                             "(Eg measure every 3 K",
                            "default_answer": 3,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1000.0,
                            "valid_options_steplength": 1e3}
                answer = self._get_input(custom_type,question,template)
                trigger_separation = answer["answer"]

                # The rate in change per minute of the controlable
                question = {"question_title": "Controlable rate",
                            "question_text": "By what amount should the controlable change per minute?",
                            "default_answer": 0.6,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1000.0,
                            "valid_options_steplength": 1e3}
                answer = self._get_input(custom_type,question,template)
                rate_for_controlable = answer["answer"]

                identifier = self._get_input(custom_type,question,template,True)
                trigger = {"start_value": start_value,
                           "end_value": end_value,
                           "trigger_separation": trigger_separation,
                           "rate_for_controlable": rate_for_controlable}
                param_controller = ParameterController(identifier, self.meas_setup, desired_controlable, trigger,
                                                       self.tasks)

            # answer being 1 means "specific values" parameter controller should be used
            elif answer["answer"] == 1:
                specific_values_list = []
                UserInput.post_status("We will generate a nice and shiny list for you. But first, I need some "
                                      "answers")
                UserInput.post_status("You are able to create an unlimited amount of lists, not just 1 separate "
                                      "low frequency list")

                # We promised unlimited lists, now we have to deliver
                user_wants_one_more_list = True
                while user_wants_one_more_list:
                    question = {"question_title": "Distribution of list",
                                "question_text": "Do you want a linear, a logarithmic distribution or single point?",
                                "default_answer": 1,
                                "optiontype": "multi_choice",
                                "valid_options": ["linear",
                                                  "logarithmic",
                                                  "single point",
                                                  "cancel"]}
                    answer = self._get_input(custom_type,question,template)

                    generated_values = []

                    if answer["answer"] == 0:
                        # linear distribution
                        # I don't know whether there will ever be the case where a negative value is desired.
                        # Omitting right now
                        UserInput.post_status("-------- Lists always include upper boundary --------")
                        question = {"question_title": "Start value",
                                    "question_text": "What is the desired start value? Please enter the value, both "
                                                     "scientific and standard notation supported (eg 1234.56 or 1e7)",
                                    "default_answer": 1,
                                    "optiontype": "free_choice",
                                    "valid_options_lower_limit": 0.0,
                                    "valid_options_upper_limit": 1e64,
                                    "valid_options_steplength": 1e16}
                        answer = self._get_input(custom_type,question,template)
                        start_value = answer["answer"]
                        question = {"question_title": "End value",
                                    "question_text": "What is the desired end value? Please enter the value, both "
                                                     "scientific and standard notation supported (eg 1234.56 or 1e7)",
                                    "default_answer": 1e7,
                                    "optiontype": "free_choice",
                                    "valid_options_lower_limit": 0.0,
                                    "valid_options_upper_limit": 1e64,
                                    "valid_options_steplength": 1e16}
                        answer = self._get_input(custom_type,question,template)
                        end_value = answer["answer"]

                        question = {"question_title": "Interval or number of values",
                                    "question_text": "Do you want interval based or number of points based?",
                                    "default_answer": 1,
                                    "optiontype": "multi_choice",
                                    "valid_options": ["interval based",
                                                      "number of points based"]}

                        answer = self._get_input(custom_type,question,template)

                        if answer["answer"] == 0:  # interval should be used to generate the list
                            question = {"question_title": "Step size",
                                        "question_text": "What step interval shall be used dear all mighty user?",
                                        "default_answer": 30.0,
                                        "optiontype": "free_choice",
                                        "valid_options_lower_limit": 0.0,
                                        "valid_options_upper_limit": 1e64,
                                        "valid_options_steplength": 1e16}
                            answer = self._get_input(custom_type,question,template)
                            step_interval = answer["answer"]

                            generated_values = Helper.create_valuelist_according_to_distribution(start_value, end_value,
                                                                                                 None, step_interval,
                                                                                                 "linear")

                        elif answer["answer"] == 1:  # amount of steps is defined and should be used
                            question = {"question_title": "Amount of steps",
                                        "question_text": "How many steps do you want?",
                                        "default_answer": 10.0,
                                        "optiontype": "free_choice",
                                        "valid_options_lower_limit": 1.0,
                                        "valid_options_upper_limit": 1e64,
                                        "valid_options_steplength": 1e0}
                            answer = self._get_input(custom_type,question,template)
                            amount_of_values = answer["answer"]

                            generated_values = Helper.create_valuelist_according_to_distribution(start_value, end_value,
                                                                                                 amount_of_values, None,
                                                                                                 "linear")

                    elif answer["answer"] == 1:
                        # Default case - logarithmic distribution
                        UserInput.post_status("-------- Lists always include upper boundary --------")
                        question = {"question_title": "Start value",
                                    "question_text": "What is the desired start value? Please enter the value, both "
                                                     "scientific and standard notation supported (eg 1234.56 or 1e7)",
                                    "default_answer": 1,
                                    "optiontype": "free_choice",
                                    "valid_options_lower_limit": 0.0,
                                    "valid_options_upper_limit": 1e64,
                                    "valid_options_steplength": 1e16}
                        answer = self._get_input(custom_type,question,template)
                        start_value = answer["answer"]
                        question = {"question_title": "End value",
                                    "question_text": "What is the desired end value? Please enter the value, both "
                                                     "scientific and standard notation supported (eg 1234.56 or 1e7)",
                                    "default_answer": 1e7,
                                    "optiontype": "free_choice",
                                    "valid_options_lower_limit": 0.0,
                                    "valid_options_upper_limit": 1e64,
                                    "valid_options_steplength": 1e16}
                        answer = self._get_input(custom_type,question,template)
                        end_value = answer["answer"]
                        question = {"question_title": "Amount of steps",
                                    "question_text": "How many steps do you want?",
                                    "default_answer": 30.0,
                                    "optiontype": "free_choice",
                                    "valid_options_lower_limit": 1.0,
                                    "valid_options_upper_limit": 1e64,
                                    "valid_options_steplength": 1e0}
                        answer = self._get_input(custom_type,question,template)
                        amount_of_values = answer["answer"]

                        generated_values = Helper.create_valuelist_according_to_distribution(start_value, end_value,
                                                                                             amount_of_values, None,
                                                                                             "logarithmic")

                    elif answer["answer"] == 2:
                        # single point

                        question = {"question_title": "Enter desired point",
                                    "question_text": "What is your desired point?",
                                    "default_answer": 45.0,
                                    "optiontype": "free_choice",
                                    "valid_options_lower_limit": 0.0,
                                    "valid_options_upper_limit": 1e64,
                                    "valid_options_steplength": 1e16}
                        answer = self._get_input(custom_type,question,template)
                        generated_values.append(answer["answer"])


                    elif answer["answer"] == 3:
                        user_wants_one_more_list = False

                    # Show the user the list and let him confirm it before adding it to the thing
                    UserInput.post_status("---------- List as follows ----------")
                    for index, value in enumerate(generated_values):
                        UserInput.post_status(str(index) + ": " + str(value))

                    question = {"question_title": "List health status",
                                "question_text": "Is this list fine?",
                                "default_answer": True,
                                "optiontype": "yes_no"}
                    answer = self._get_input(custom_type,question,template)

                    if answer:  # means: User finds this list to suit his needs
                        for value in generated_values:
                            specific_values_list.append(value)

                    # We catch a cancel call in the original question, we then shouldn't ask the user whether he wants
                    # another list then again
                    if user_wants_one_more_list:
                        question = {"question_title": "One more?!",
                                    "question_text": "Do you want to create another list/point?",
                                    "default_answer": True,
                                    "optiontype": "yes_no"}
                        answer = self._get_input(custom_type,question,template)
                        user_wants_one_more_list = answer["answer"]
                        if user_wants_one_more_list:
                            UserInput.post_status("---------- Current list is as follows ----------")
                            for index, value in enumerate(specific_values_list):
                                UserInput.post_status(str(index) + ": " + str(value))

                identifier = self._get_input(custom_type,question,template,True)
                trigger = {"specific_values": specific_values_list}
                param_controller = ParameterController(identifier, self.meas_setup, desired_controlable, trigger,
                                                       self.tasks)
            self.tasks.append(param_controller)

        # 1 = DataAcquisition, code path to create a new Data Acquisition task
        elif answer["answer"] == 1:
            question = {"question_title": "Choosing the measurable",
                        "question_text": "What do you want to measure?",
                        "default_answer": 0,
                        "optiontype": "multi_choice",
                        "valid_options": available_measurables}
            answer = self._get_input(custom_type,question,template)
            measurable_to_measure = available_raw_measurables[answer["answer"]]
            question = {"question_title": "max deviation values during sub_tasks",
                        "question_text": "It is possible to output the maximum deviation while sub_tasks were run. "
                                         "Do you want that?",
                        "default_answer": True,
                        "optiontype": "yes_no"}
            answer = self._get_input(custom_type,question,template)
            user_wants_max_deviation = answer["answer"]
            identifier = self._get_input(custom_type,question,template,True)
            new_data_acqu = DataAcquisition(identifier, self.meas_setup, measurable_to_measure,
                                            user_wants_max_deviation, self.tasks)
            self.tasks.append(new_data_acqu)

        # 2 = Trigger - either measurable triggered or time triggered for now
        elif answer["answer"] == 2:

            question = {"question_title": "Time or Measurable triggered",
                        "question_text": "Do you want to have it triggered by time or a measurable "
                                         "(not implemented yet)?",
                        "default_answer": 0,
                        "optiontype": "multi_choice",
                        "valid_options": ["time", "meausurable"]}
            answer = self._get_input(custom_type,question,template)

            # 0 means time triggered
            if answer["answer"] == 0:
                question = {"question_title": "Total time",
                            "question_text": "Please enter the total time in minutes",
                            "default_answer": 10.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1e64,
                            "valid_options_steplength": 1e16}
                answer = self._get_input(custom_type,question,template)
                total_time = answer["answer"]
                question = {"question_title": "Trigger separation",
                            "question_text": "Please enter the trigger separation in minutes. "
                                             "Eg every 3 minutes",
                            "default_answer": 3.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1e64,
                            "valid_options_steplength": 1e16}
                answer = self._get_input(custom_type,question,template)
                trigger_separation = answer["answer"]

                trigger = {"total_time_span": total_time, "trigger_separation": trigger_separation}
                identifier = self._get_input(custom_type,question,template,True)

                new_trigger = Trigger(identifier, self.meas_setup, trigger, self.tasks)
                self.tasks.append(new_trigger)


            # 1 means measurable triggered acquisition
            elif answer["answer"] == 1:
                question = {"question_title": "Measurable used to trigger sub task",
                            "question_text": "Which measurable do you want to use to trigger a sub task?",
                            "default_answer": 0,
                            "optiontype": "multi_choice",
                            "valid_options": available_raw_measurables}
                answer = self._get_input(custom_type,question,template)
                measurable_to_use_as_trigger = available_measurables[answer["answer"]]

                question = {"question_title": "Trigger value",
                            "question_text": "At what value should it trigger?",
                            "default_answer": 310.0,
                            "optiontype": "free_choice",
                            "valid_options_lower_limit": 0.0,
                            "valid_options_upper_limit": 1e64,
                            "valid_options_steplength": 1e16}
                answer = self._get_input(custom_type,question,template)
                triggering_value = answer["answer"]

                question = {"question_title": "Trigger threshold direction",
                            "question_text": "Should it be triggered when below the specified value? "
                                             "(saying NO means it triggers above the value",
                            "default_answer": True,
                            "optiontype": "yes_no"}
                answer = self._get_input(custom_type,question,template)
                trigger_when_below = answer["answer"]

                trigger = {"acquis_triggering_measurable": measurable_to_use_as_trigger,
                           "acquis_triggering_value": triggering_value,
                           "acquis_triggered_when_below_value": trigger_when_below}
                identifier = self._get_input(custom_type,question,template,True)

                # new_trigger = Trigger...
                # self.tasks.append(new_trigger)...

        # a task itself is an object and not the identifier but we need to sort by identifier - lambda is a way to
        # access the underlying identifier for sorting.
        # As we have a sort of arbitrary insertion point for tasks into the list, we append and then sort the list. To
        # never screw up, we directly sort after each insert/append.
        self.tasks.sort(key=lambda x: x.identifier)

    def _get_id_for_task_insert_into_queue(self):
        if len(self.tasks) == 0:
            id_for_task = [0]
        else:
            available_ids = []
            task_id_list = []
            for item in self.tasks:
                current_identifier = item.identifier.copy()
                task_id_list.append(current_identifier)
            # After this, we have a nice list containing all the identifiers and also knowledge about
            # what the deepest level is

            for index, item in enumerate(task_id_list):
                own_length = len(item)
                later_own_index_length_exists = False
                has_sub_identifier = False
                smaller_list = task_id_list[(index + 1):]
                for subitem in smaller_list:
                    if len(subitem) < own_length:
                        break
                    elif len(subitem) == own_length:
                        later_own_index_length_exists = True
                    elif len(subitem) > own_length:
                        has_sub_identifier = True

                if not has_sub_identifier:
                    new_sub_identifier = item.copy()
                    new_sub_identifier.append(0)
                    available_ids.append(new_sub_identifier)

                if not later_own_index_length_exists:
                    new_identifier_one = item.copy()
                    new_identifier_one[len(new_identifier_one) - 1] += 1
                    available_ids.append(new_identifier_one)

            available_string_ids = []
            available_ids.sort()

            for item in available_ids:
                available_string_ids.append(str(item))

            self.print_current_task_list()

            question = {"question_title": "Insertion point",
                        "question_text": "Which insertion point do you want to use?",
                        "default_answer": 0,
                        "optiontype": "multi_choice",
                        "valid_options": available_string_ids}
            answer = UserInput.ask_user_for_input(question)
            id_for_task = available_ids[answer["answer"]]
        return id_for_task

    def print_current_task_list(self):
        UserInput.post_status("This is the current task list:")

        for task in self.tasks:
            UserInput.post_status(str(task.identifier) + "task " + task.generate_one_line_summary())

    def measure(self):
        """
            We start going through all tasks and every task starts sub_tasks accordingly
        """
        first_temp_file = True
        self._prepare_before_measuring()
        for task in self.tasks:
            task.start()

        for task in self.tasks:
            if len(task.identifier) == 1:
                task.should_do_now = True
                while task.should_do_now:
                    if first_temp_file:
                        main_db.pickle_database("_autosave1")
                        first_temp_file = False
                        time.sleep(300)
                    else:
                        main_db.pickle_database("_autosave2")
                        first_temp_file = True
                        time.sleep(300)
                task.should_do_now = False

        for task in self.tasks:
            task.should_be_running = False
            task.join()
        self.meas_setup.measurement_done()

    def _prepare_before_measuring(self):
        # save the current task list in the database. Crucial for later data manipulation
        task_list = []
        for task in self.tasks:
            task_list.append(str(task.identifier) + "task " + task.generate_one_line_summary())
        main_db.tasks = task_list

    def remove_task(self):
        """Method to remove a task from the task list

        """

        one_line_summary_of_tasks = []
        for task in self.tasks:
            one_line_summary_of_tasks.append(str(task.identifier) + "task " + task.generate_one_line_summary())

        question = {"question_title": "Remove task",
                    "question_text": "Please select the task you want to have removed.",
                    "default_answer": 2,
                    "optiontype": "multi_choice",
                    "valid_options": one_line_summary_of_tasks}

        to_be_removed_index = UserInput.ask_user_for_input(question)["answer"]

        sub_tasks = Helper.check_for_sub_tasks(self.tasks[to_be_removed_index].identifier, self.tasks)

        if len(sub_tasks) == 0:
            self.tasks.pop(to_be_removed_index)
        else:
            question = {"question_title": "Warning, Sub_tasks detected!",
                        "question_text": "The selected task has sub_tasks. Do you really want to delete it?",
                        "default_answer": True,
                        "optiontype": "yes_no"}
            user_wants_removal = UserInput.ask_user_for_input(question)["answer"]
            if user_wants_removal:
                amount_of_subtasks = len(sub_tasks)
                for index in range(amount_of_subtasks):
                    self.tasks.pop(to_be_removed_index + 1 + index)
                self.tasks.pop(to_be_removed_index)
            else:
                UserInput.post_status("Didn't remove a thing. Carry on!")
                
    def _get_input(self,custom,question,template=[],task_queue=False):
        """ 

        Parameters
        ----------
        custom : Boolean
            Decide wether to customize your measurement or use a template instead.
        question :
            Enter the posed question.
        template : 
            Enter a template, if custom=False.

        Returns chosen task.
        -------
        Private function in order to implement template measurements. A list with all input parameters
        serves as template.
        
        """
        if custom:
            answer = UserInput.ask_user_for_input(question)
            self.task_input.append(answer["answer"])
            return answer
        else:
            if task_queue:
                return self._get_id_for_task_insert_into_queue()
            else:  
                return {'answer': template.pop(0)}
        
                
   


class Helper:
    """This class bundles static methods helping with general value manipulation and stuff"""

    @staticmethod
    def check_for_sub_tasks(identifier: [], global_task_list: []):
        """ This method fills the list of sub_tasks that can then easily be called when running the whole task.
        """
        sub_tasks = []
        own_id = identifier
        # initialize own position in list (which is really just the index of the item at hand in the global list
        own_position_in_list = int
        # ok, we want to find ourselves:
        for index, item in enumerate(global_task_list):
            if own_id == item.identifier:
                own_position_in_list = index

        # now make a copy of the global list, and shorten it so it starts with us. As the global list is sorted, we can
        # simply check if the next item has a shorter identifier or an identifier of equal length to know whether the
        # next item is a sub_task or a task on the same level
        temporary_global_list = global_task_list.copy()
        temporary_global_list = temporary_global_list[(own_position_in_list + 1):]
        own_length = len(own_id)
        for item in temporary_global_list:
            if len(item.identifier) == own_length + 1:
                sub_tasks.append(item)
            elif len(item.identifier) <= own_length:
                break
            else:
                pass
        return sub_tasks

    @staticmethod
    def create_valuelist_according_to_distribution(start_value: float, end_value: float, amount_of_values,
                                                   step_interval,
                                                   distribution: ""):
        """Generates a population of values, can create a logarithmic population with amount_of_values set (includes
        the end value in the counting), or can be used to calculate linear populations, those either by amount of
        desired values or by step_interval, always including upper boundary
        :param start_value: the start value
        :param end_value:
        :param amount_of_values:
        :param step_interval:
        :param distribution: either "logarithmic" or "linear"
        :return:
        """
        values = []
        if distribution == "logarithmic":
            start_log = math.log10(start_value)
            end_log = math.log10(end_value)

            log_diff = end_log - start_log
            log_step = log_diff / (amount_of_values - 1)

            # The usual routine asking for numbers returns a float, but that doesn't work here
            amount_of_values = int(amount_of_values)

            for current_step in range(amount_of_values):
                values.append(math.pow(10, start_log + current_step * log_step))
        elif distribution == "linear":
            if amount_of_values:  # we have a specified amount of values, not a specified interval
                # We subtract 1 at amount of values as the upper value has to be included
                step_interval = (end_value - start_value) / (amount_of_values - 1)
                for current_step in range(amount_of_values):
                    values.append(start_value + (current_step * step_interval))
            elif step_interval:
                end_value_is_smaller_than_start_value = False
                if end_value < start_value:
                    end_value_is_smaller_than_start_value = True
                    temporary_value = start_value
                    start_value = end_value
                    end_value = temporary_value
                for value in range(start_value, end_value, step_interval):
                    values.append(value)
                # we have to make sure that if appropriate the end temperature is included as well as well as a smaller
                # last step:
                if not values[len(values) - 1] == end_value:
                    sweep_target_temperature = values[len(values) - 1] + step_interval
                    if sweep_target_temperature == end_value:
                        values.append(sweep_target_temperature)
                    else:
                        values.append(end_value)
                if end_value_is_smaller_than_start_value:
                    values_old = values
                    values = []
                    for i in range(len(values_old)):
                        new_value = end_value + start_value - values_old[i]
                        values.append(new_value)
        return values

    @staticmethod
    def create_string_from_mes_device_data_for_raw_file(result: [[], []]):
        """

        :param result: a defined standard result list from a mes device
        :return: a string with all values separated by tab with a format: explanation at the end
        """

        descriptor_for_result = result[0]
        string_for_raw_file = ""
        for item in result[1]:
            string_for_raw_file = string_for_raw_file + str(item) + "    "
        string_for_raw_file = string_for_raw_file + "format: " + str(descriptor_for_result)
        return string_for_raw_file

