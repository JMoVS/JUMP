"""This is a module to implement the hardware side of the commands to send through the GPIB interface to the Measuremnt
hardware devices. It responds to predefined methods and returns correctly calculated values back to the
MeasurementDeviceController"""
__copyright__ = "Copyright 2015 - 2017, Justin Scholz"
__author__ = "Justin Scholz"

import time, datetime
from abc import ABCMeta, abstractmethod, abstractproperty
from importlib import import_module

import UserInput
import visa
from pyvisa.resources.gpib import GPIBInstrument  # We want to set our dev individually so code completion works
from pyvisa.resources.messagebased import MessageBasedResource


def importer(device_class, idn_name_to_import, idn_alias_to_import):
    """
    Imports device serials and names gracefully so you don't have to have serial files for devices you don't own. It
    receives the expected
    :param device_class: the name of the serial file as string
    :param idn_name_to_import: the name of the device-name in the serial file as string
    :param idn_alias_to_import: the name of the device-alias in the serial file as string
    :return: idn_alias_to_import, idn_alias_to_import
    """
    try:
        import_name = "Device_Serials." + device_class
        dev_information = import_module(import_name)
        idn_name_to_import = getattr(dev_information, idn_name_to_import)
        idn_alias_to_import = getattr(dev_information, idn_alias_to_import)

    except ImportError:
        idn_name_to_import = ["Device Serial file not present"]
        idn_alias_to_import = "Device Serial file not present"

    return idn_name_to_import, idn_alias_to_import


class MeasurementDeviceController:
    """The purpose of the MeasurementDeviceController is to abstract the hardware away from the measurement logic. It
    shouldn't matter whether it is an Alpha Analyzer or something else. Therefore this module will create objects
    for the respective hardware python class and send commands there.
    MeasurementDeviceController objects adhere to standard methods to be controlled by other objects to provide
    an abstract way of accessing the hardware
    """

    def __init__(self, resource_manager: visa.ResourceManager):
        """init method should ready a list of devices with their accompanying *IDN? information. These answers will be
        stored in the idn_list[] variable"""
        self.dev_resource_manager = resource_manager
        self.recognized_devs = []
        self.mes_device = None
        """:type :MeasurementDevice"""
        self.select_device()
        self.initialize_device()
        self.name = self.mes_device.idn_alias
        return

    def _create_list_of_connected_devs(self):
        list_of_resources = self.dev_resource_manager.list_resources_info(query='?*::INSTR')
        self.idn_list = []
        for instrument in list_of_resources:
            instrument_instance = self.dev_resource_manager.open_resource(instrument)
            """:type :MessageBasedResource"""
            # set the communication time out so it doesn't wait 2.5 seconds per device! This value is in milliseconds
            instrument_instance.timeout = 50
            try:
                self.idn_list.append((instrument, instrument_instance.query('*IDN?')))
            except visa.VisaIOError:
                try:
                    # Agilent/HP3458A doesn't adhere to standards. That's why we need to do this here
                    instrument_instance.write("END ALWAYS")
                    self.idn_list.append((instrument, instrument_instance.query('ID?')))
                except visa.VisaIOError:
                    pass
            instrument_instance.close()
        self.idn_list.append((None,"NIMaxScreenshots"))

    def initialize_device(self):
        """method to initialize the device to be ready for measurement"""
        self.mes_device.initialize_instrument()
        return

    def check_controlable_for_compatibility(self, controlable_to_be_changed, list_of_values_of_controlable: []):
        """Checks the actual_controlable list with the hardware and returns a modified actual_controlable list if necessary
        :param list_of_values_of_measurable: []
        :return: hardware_possible_values_for_measurable
        """
        hardware_possible_values_for_measurable = []
        for controlable_value in list_of_values_of_controlable:
            actual_controlable = self.mes_device.set_controlable(controlable_to_be_changed, controlable_value)
            hardware_possible_values_for_measurable.append(actual_controlable)
        return hardware_possible_values_for_measurable

    def measure_measurable(self, measurable_to_measure):
        """
        :param measurable_to_measure: The specific measurable the device should measure. In case of an ALPHA for
        example, it's irrelevant as it will only ever measure frequency response right now. But a temperature
        controller has different sensors so we may want to check sensor A or sensor B
        :return: [[descriptor_for_results],[list_of_results_according_to_descriptor_of_results]
        descriptor_for_results: a list containing descriptors what measured_1 and measured_2 are (eg R and X)
        measured_freq: one may send one frequency to the device, but the measurementDevice may choose to measure a
        different one. Here we state (if possible and returned) the actual one

        """
        return self.mes_device.measure_measurable(measurable_to_measure)

    def set_controlable(self, dev_controlable_dict: dict):
        result_dict = self.mes_device.set_controlable(dev_controlable_dict)
        return result_dict

    @property
    def controlables(self):
        return self.mes_device.controlables

    @property
    def measurables(self):
        return self.mes_device.measurables

    def _detect_devices(self):
        self._create_list_of_connected_devs()
        mes_dev_choos_helper = MeasurementDeviceChooser()
        for item in self.idn_list:
            self.recognized_devs = mes_dev_choos_helper.detect_devices(item[0], item[1])

    def select_device(self):
        self.recognized_devs.clear()
        self._detect_devices()
        mes_dev_choos_helper = MeasurementDeviceChooser()
        failed = False
        if len(self.recognized_devs) == 0:
            failed = True
        elif len(self.recognized_devs) == 1:

            print("Recognized the following measurement device. Do you want to select this?")
            print(self.recognized_devs[0][1])
            question = {"question_title": "1 device detected",
                        "question_text": "The device " + self.recognized_devs[0][2] + " was detected. Select?",
                        "default_answer": True, "optiontype": "yes_no"}
            answer = UserInput.ask_user_for_input(question)["answer"]
            if answer:
                mes_dev_choos_helper.select_device(self.recognized_devs[0], self.dev_resource_manager)
                self.mes_device = mes_dev_choos_helper.mes_device
            else:
                failed = True
        elif len(self.recognized_devs) > 1:

            valid_options = []
            for index, instrument in enumerate(self.recognized_devs):
                valid_options.append(instrument[2])
            question = {"question_title": "Detected devices",
                        "question_text": "{0} measurement devices were found. "
                                         "Which one do you want to use?".format(len(self.recognized_devs)),
                        "default_answer": 0,
                        "optiontype": "multi_choice",
                        "valid_options": valid_options}
            answer = UserInput.ask_user_for_input(question)["answer"]
            mes_dev_choos_helper.select_device(self.recognized_devs[answer], self.dev_resource_manager)
            self.mes_device = mes_dev_choos_helper.mes_device
        if failed:
            UserInput.post_status("no measurement devices recognized")
            UserInput.post_status("The hardware is reporting to be:")
            iterator = 0
            for dev in self.idn_list:
                # We have to remove the last 2 characters or else it won't display (last characters are \x00\r)
                UserInput.post_status("#{0}: {1}: {2}".format(iterator, dev[0], (dev[1][:-2])))
                iterator += 1
            UserInput.confirm_warning("Please retry detecting devices and make sure all "
                                      "hardware connectors are plugged in tightly.")
            self.select_device()


################################################

class MeasurementDevice(metaclass=ABCMeta):
    """This can be considered as the general layout of all the hardware device classes. These methods will always be present but may
    return False if they are not implemented
    :type mes_device : MeasurementDevice
    """

    # We need this so device detection of multiple devices works


    # This will later be set to the user chosen device idn
    idn_name = "Something should be here"

    def __init__(self):
        self.recognized_devs = []
        self.mes_device = None
        self.visa_instrument = None
        self.res_man = None
        """":type : visa.ResourceManager"""
        self.measurables = []
        self.controlables = []
        self.idn_alias = None

    @abstractmethod
    def initialize_instrument(self):
        return

    @abstractmethod
    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        return

    @abstractmethod
    def select_device(self, recognized_dev: [], resource_manager: visa.ResourceManager):
        return

    @abstractmethod
    def measure_measurable(self, measurable_to_measure):
        """

        :return:
        """
        return

    @abstractmethod
    def set_controlable(self, controlables_dict: {}):
        return controlables_dict

    def set_visa_dev(self, instrument: visa.Resource, resource_manager: visa.ResourceManager):
        self.visa_instrument = resource_manager.open_resource(instrument)
        return


class ALPHA(MeasurementDevice):
    """The class for the hardware command implementation of the Alpha Analyzer """
    idn_name_Alpha, idn_alias_Alpha = importer("ALPHA", "idn_name_Alpha", "idn_alias_Alpha")

    measurables = ["RX"]
    controlables = ["expected_freq"]

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        for Alpha_ID in self.idn_name_Alpha:
            if Alpha_ID in should_be_selected_dev[1]:
                self.mes_device = ALPHA()
                self.mes_device.visa_instrument = None
                """:type :MessageBasedResource"""

                self.mes_device.idn_name = Alpha_ID
                self.mes_device.idn_alias = self.idn_alias_Alpha
                self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
                self.mes_device.controlables = ALPHA.controlables
                self.mes_device.measurables = ALPHA.measurables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_Alpha:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, self.idn_alias_Alpha))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        """This will initialize the visa dev and if necessary, ask the user about his choosing if there are options.

        """
        self.visa_instrument.write("*RST")  # soft reset
        successful = False
        while not successful:
            try:
                successful = self._command_status_parsing(self.visa_instrument.query("*IDN?"))[0]  # we may have to wait
                # a little
            except visa.VisaIOError:
                time.sleep(0.1)
        time.sleep(1)
        result = self.visa_instrument.query("MODE=IMP")  # Impedance measurement mode
        if not ALPHA._command_status_parsing(result)[0]:
            print(result[1])
            print("You should probably start over.")

        result = self.visa_instrument.query("ZLLCOR=1")  # Enable low loss correction
        if not ALPHA._command_status_parsing(result)[0]:
            print(result[1])
            print("Failed to set low loss correction.")

        self._set_measurement_mode()  # We want to know whether it's 2,3 or 4 point measurement mode
        self._set_driven_shield()  # Driven shields?
        self._calibrate_alpha()  # Calibration?
        self._connection_check()  # Connection check necessary/wanted?
        self._activate_short_load()  # activate short load?
        self._activate_reference_measurement()  # Activate reference measurement?

        successful_execution = False
        while not successful_execution:
            question = {"question_title": "Excitation voltage",
                        "question_text": "Please enter an excitation voltage between 0 and 3 V. Maximum accuracy is 0.1 V.",
                        "default_answer": 1.0,
                        "optiontype": "free_choice",
                        "valid_options_lower_limit": 0.0,
                        "valid_options_upper_limit": 3.0,
                        "valid_options_steplength": 1e1}
            answer = UserInput.ask_user_for_input(question)["answer"]
            successful_execution = self._set_ac_excitation_voltage(answer)
        self._set_minimum_measurement_time()  # Set default minimum measurement time (0.5s)

    def measure_measurable(self, measurable_to_measure):
        """

        :param measurable_to_measure: not used in ALPHA, we always measure frequency right now
        :return: result. In case of ALPHA: {"R": measured_R, "X": measured_X,
        "freq": measured_freq,"successful": successful_measurement, "message": message}
        """

        # Start the measurement!
        self.visa_instrument.write("MST")
        # None means here that we wait indefinitely!! (23 day measurements for the win!! ;-) )
        self.visa_instrument.wait_for_srq(None)

        # get the measurement data
        response = self.visa_instrument.query("ZRE?")
        successful_execution, message = ALPHA._command_status_parsing(response)
        if not successful_execution:
            print(message)
            print("Couldn't measure the frequency.")
        # TODO: THis could probably be changed to just use .query_asci_values to not have to parse manually
        successful_measurement, message, measured_R, measured_X, measured_freq = self._parse_results(response)
        if not successful_measurement:
            print(message)
            # we shouldn't save incorrect measurement data # TODO: Should we really be that hard?!
            measured_R = None
            measured_X = None
            measured_freq = None

        result = {"R": measured_R, "X": measured_X, "freq": measured_freq, "successful_alpha": successful_measurement,
                  "message_alpha": message, "time_alpha": time.strftime("%d.%m.%Y %H:%M:%S")}

        return result

    def set_controlable(self, controlable_dict: {}):
        """


        :param controlable_dict: {"expected_freq": 1.3}, a dictionary containing the identifier and the new value
        :return: controlable_dict with the actual value
        """

        self.visa_instrument.write("GFR=" + str(controlable_dict["expected_freq"]))
        response = self.visa_instrument.query("GFR?")
        successful_execution, message = ALPHA._command_status_parsing(response)
        freq = 0
        if not successful_execution:
            UserInput.post_status(message)
            UserInput.post_status("Couldn't get accurate frequency.")
        else:
            # this is ugly code and probably, all of the ALPHA should change to query_asci_values...
            gfr, freq = message.split(sep="=")
            freq = float(freq)
        return {"expected_freq": freq}

    def _set_measurement_mode(self):
        """Asks the user which measurement mode he prefers and sets it accordingly

        """
        self.measurement_mode = int
        question = {"question_title": "Measurement Mode",
                    "question_text": "Please choose which measurement mode to use", "default_answer": 2,
                    "optiontype": "multi_choice", "valid_options": ["2-point", "3-point", "4-point"]}
        self.measurement_mode = 2 + UserInput.ask_user_for_input(question)["answer"]
        # The ALPHA accepts 2, 3 or 4 as value, the standard return is 0,1 or 2 so we have to add 2

        response = self.visa_instrument.query("FRS=" + str(self.measurement_mode))  # Actually set the measurement mode
        successful_execution, message = ALPHA._command_status_parsing(response)
        if not successful_execution:
            UserInput.post_status(message)
            UserInput.post_status("We failed to set the measurement mode. Something is wrong. "
                                  "Is the ZG4 or POT/GAL connected properly?")

    def _set_driven_shield(self):
        """ Ask the user for preference and set driven shield yes/no


        """
        self.driven_shield = (int, int)
        question = {"question_title": "Driven shields",
                    "question_text": "Do you want to use driven shields?", "default_answer": 0,
                    "optiontype": "multi_choice",
                    "valid_options": ["no", "yes: Drive V high shield", "yes: Drive V low shield",
                                      "yes: Drive both shields"]}
        answer = UserInput.ask_user_for_input(question)["answer"]

        if answer == 0:
            self.driven_shield = (0, 0)
        elif answer == 1:
            self.driven_shield = (1, 0)
        elif answer == 2:
            self.driven_shield = (0, 1)
        elif answer == 3:
            self.driven_shield = (1, 1)

        response = self.visa_instrument.query("DRS=" + str(self.driven_shield[0]) + " " + str(self.driven_shield[1]))
        successful_execution, message = ALPHA._command_status_parsing(response)
        if not successful_execution:
            UserInput.post_status(message)
            UserInput.post_status("Driven shield mode couldn't be set!")

    def _calibrate_alpha(self):
        """ This method asks about the ALPHA specific calibration preferences (no, fast, full or short_load)


        """
        self.was_calibrated = int  # 0 = no, 1 = fast calibration, 2 = full calibration, 3 = short load calibration
        question = {"question_title": "Calibration",
                    "question_text": "Calibrate this black Alpha box?",
                    "default_answer": 0,
                    "optiontype": "multi_choice",
                    "valid_options": ["no calibration", "fast calibration (recommended)",
                                      "full calibration (approximately 30-60 minutes)",
                                      "Perform low impedance short-load calibration"]}
        answer = UserInput.ask_user_for_input(question)["answer"]
        if answer == 0:  # no calibration (default)
            self.was_calibrated = 1
            UserInput.post_status("No calibration was done.")
        elif answer == 1:  # fast calibration
            # Due to the infamous ALPHA bug, we set the measurement mode to 2-point first:
            response = self.visa_instrument.query("FRS=2")
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't set measurement mode to 2-point for calibration. Please start over.")

            # Now calibrate
            response = self.visa_instrument.query("ZRUNCAL=REF_INIT")
            successful_execution, message = ALPHA._command_status_parsing(
                response)  # TODO: Check behaviour here with the query
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't initialize the Calibration. Please restart the program.")
            UserInput.confirm_warning("Please disconnect all cables that could cause an impedance!")

            self.visa_instrument.write("ZRUNCAL=REF")  # this command should be checked for with a srq:
            UserInput.post_status("Please wait a moment. Started at: " + time.strftime("%c"))
            self.visa_instrument.wait_for_srq(None)
            response = self.visa_instrument.read()
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't perform fast calibration.")
            else:
                self.was_calibrated = 2
                UserInput.post_status("Calibration succeeded")

            response = self.visa_instrument.query("FRS=" + str(self.measurement_mode))
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("We failed to set the measurement mode. Something is wrong. "
                                      "Is the ZG4 or POT/GAL connected properly?")

        elif answer == 2:  # full calibration
            # Due to the infamous ALPHA bug, we set the measurement mode to 2-point first:
            response = self.visa_instrument.query("FRS=2")
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't set measurement mode to 2-point for calibration. Please start over.")

            # Now calibrate
            response = self.visa_instrument.query("ZRUNCAL=ALL_INIT")
            successful_execution, message = ALPHA._command_status_parsing(
                response)  # TODO: Check behaviour here with the query
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't initialize the Calibration. Please restart the program.")
            UserInput.confirm_warning("Please disconnect all cables that could cause an impedance!")

            self.visa_instrument.write("ZRUNCAL=ALL")
            UserInput.post_status("This can take up to an hour. No status update will be shown. Please be patient!")
            UserInput.post_status("Calibration started at: " + time.strftime("%c"))
            self.visa_instrument.wait_for_srq(None)
            response = self.visa_instrument.read()
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't perform Calibration. Please start over")
            else:
                self.was_calibrated = 3
                UserInput.post_status("Calibration succeeded")

            response = self.visa_instrument.query("FRS=" + str(self.measurement_mode))
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("We failed to set the measurement mode. Something is wrong. "
                                      "Is the ZG4 or POT/GAL connected properly?")

        elif answer == 3:  # short load calibration
            response = self.visa_instrument.query("ZRUNCAL=SL_INIT")
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't initialize low impedance short load calibration. "
                                      "Try restarting the program and the ALPHA!")
            UserInput.confirm_warning("Please connect the short calibration standard.")

            self.visa_instrument.write("ZRUNCAL=SL_SHORT")  # again, srq method
            UserInput.post_status("Calibrating short load. Started at: " + time.strftime("%c"))
            self.visa_instrument.wait_for_srq()
            response = self.visa_instrument.read()
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status(
                    "Could not calibrate short load. Look at error message above and consider a restart.")

            UserInput.confirm_warning("Please connect the 100" + u"\u03A9" + " load calibration standard.")
            self.visa_instrument.write("ZRUNCAL=SL_100")
            UserInput.post_status("Performing 100" + u"\u03A9" + " calibration. Started at: " + time.strftime("%c"))
            self.visa_instrument.wait_for_srq()
            response = self.visa_instrument.read()
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Error during 100" + u"\u03A9" + " calibration. Consider starting over.")
            else:
                self.was_calibrated = 4
                UserInput.post_status("Calibration succeeded")

    def _connection_check(self):
        """ A connection check might be (depending on connected gear and previously run calibrations) necessary


        """
        response = self.visa_instrument.query("ZCON_TO_CHECK?")
        self.connections_checked = False
        successful_execution, message = ALPHA._command_status_parsing(response)
        response = response[:-2]
        if not successful_execution:
            UserInput.post_status(message)
            UserInput.post_status("Refer to the error message and the ALPHA display, we only wanted to check a status!")
        else:  # well, it succeeded telling us its needs of connection checks
            if response == "ZCON_TO_CHECK=0":  # '0' means that it doesn't require a check
                if self.was_calibrated == 1:  # if it was not calibrated, this test was never run, but also isn't
                    # required. Purly optional nature.
                    question = {"question_title": "Connection check",
                                "question_text": "Connection check wasn't performed but is optional. Do you want to check the connections?",
                                "default_answer": True,
                                "optiontype": "yes_no"}
                    answer = UserInput.ask_user_for_input(question)["answer"]
                    if answer:
                        UserInput.confirm_warning("Make sure all cables are connected properly!")
                        self.visa_instrument.write("ZRUNCAL=CONCHECK")  # CONCHECK is considered a calibration task
                        # and therefore should be handled via srq
                        UserInput.post_status(
                            "Running connection test, pls hold tight. Started at: " + time.strftime("%c"))
                        self.visa_instrument.wait_for_srq()
                        response = self.visa_instrument.read()
                        successful_execution, message = ALPHA._command_status_parsing(response)
                        if not successful_execution:
                            UserInput.post_status(message)
                            UserInput.post_status("Connection test failed. You can give it another try if you want to.")
                            self._connection_check()
                        else:
                            self.connections_checked = True
                            UserInput.post_status("Connections tested successfully!")
                else:
                    self.connections_checked = True  # ALPHA does connection check during calibration
            elif response == "ZCON_TO_CHECK=1":
                UserInput.post_status("The ALPHA is requiring a connection check.")
                UserInput.confirm_warning("Please connect all cables.")
                self.visa_instrument.write("ZRUNCAL=CONCHECK")  # CONCHECK is considered a calibration task
                # and therefore should be handled via srq
                UserInput.post_status("Running connection test, pls hold tight. Started at: " + time.strftime("%c"))
                self.visa_instrument.wait_for_srq()
                response = self.visa_instrument.read()
                successful_execution, message = ALPHA._command_status_parsing(response)
                if not successful_execution:
                    UserInput.post_status(message)
                    UserInput.post_status("Connection test failed. You can give it another try if you want to.")
                    self._connection_check()
                else:
                    self.connections_checked = True
            else:
                UserInput.post_status(message)
                UserInput.post_status(
                    "Couldn't get the status of the concheck. Something is wrong. A least the ALPHA didn't "
                    "respond properly to the ZCON_TO_CHECK? command.")
                self._connection_check()  # TODO: Think concheck through and see whether it is implemented correctly

    def _activate_short_load(self):
        """ A method to ask whether user wants to use short_load or not


        """
        question = {"question_title": "Short Load calibration",
                    "question_text": "Do you want to use short-load calibration?", "default_answer": False,
                    "optiontype": "yes_no"}
        answer = UserInput.ask_user_for_input(question)["answer"]
        if answer:  # user wanted to use short load calibration
            response = self.visa_instrument.query("ZSLCAL=1")
            self.short_load_activated = True
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't activate short load calibration.")
        elif not answer:  # default: off
            response = self.visa_instrument.query("ZSLCAL=0")
            self.short_load_activated = False
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't set short load calibration to off.")

    def _activate_reference_measurement(self):
        """ A method to ask the user whether he wants to use a reference measurement and set it accordingly


        """
        question = {"question_title": "Reference measurement.",
                    "question_text": "Enable reference measurement (recommended)?", "default_answer": True,
                    "optiontype": "yes_no"}
        answer = UserInput.ask_user_for_input(question)["answer"]
        if answer:  # user wanted to
            # use short load calibration
            response = self.visa_instrument.query("ZREFMODE=-3")
            self.reference_measurement_activated = True
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Couldn't set reference measureent to on (-3).")
        elif not answer:
            response = self.visa_instrument.query("ZREFMODE=0")
            self.reference_measurement_activated = False
            successful_execution, message = ALPHA._command_status_parsing(response)
            if not successful_execution:
                UserInput.post_status(message)
                UserInput.post_status("Failed to deactivate reference measurement!")

    def _set_ac_excitation_voltage(self, voltage: float):
        """ AC excitation voltage can be set per measurement point.

        :param voltage: AFAIK a value with one digit after the dot valuable
        :return: Bool: whether it was successful or not
        """
        response = self.visa_instrument.query("ACV=" + str(voltage))  # Set default excitation voltage
        successful_execution, message = ALPHA._command_status_parsing(response)
        successful = bool  # to return whether this method was successfull or not
        if successful_execution:
            self.excitation_voltage = voltage
        return successful_execution

    def _set_minimum_measurement_time(self, seconds=0.5):
        """ Sets the minimum measurement time.

        :param seconds: the value for the minimum measurement time
        :return: Bool: Whether it was successful in setting it or not.
        """
        response = self.visa_instrument.query("MTM=" + str(seconds))
        successful_execution, message = ALPHA._command_status_parsing(response)
        if not successful_execution:
            UserInput.post_status(message)
        elif successful_execution:
            self.minimum_measurement_time = seconds
        return successful_execution

    @staticmethod
    def _command_status_parsing(response: str):
        """

        :param response: pass the result of a read to see whether the command executed fine!
        :return: successful: when the result is "OK" or something else, it returns True; message: A message
        describing the error code according to the Manual
        """
        response = response[:-2]
        message = response  # if it is not overriden later, the message is supposed to be the result
        if response == "OK":
            successful = True
        elif response == "CA":
            successful = False
            message = "Cannot execute this command during active calibration."
        elif response == "CR":
            successful = False
            message = "A measurement was started which requires a test interface calibration which does not exist. \n " \
                      "The ALPHA will: \n Recalibrate interface, *type* Sno=*Interface* *Serial Number* *Calibration" \
                      " type* \n whereas *Calibration type* specifies the required calibration. Perform " \
                      "calibration as described in 2005 ALPHA manual calibration chapter."
        elif response == "CN":
            successful = False
            message = "The received command is unavailable while the CE output of a POT/GAL interface *is* connected."
        elif response == "EC":
            successful = False
            message = "System connection test required. You should try to calibrate the device."
        elif response == "ER":
            successful = False
            message = "General command error. Depends on the issued command."
        elif response == "HR":
            successful = False
            message = "The reference calibration for the IMP_HV150 us invalid. You should try to calibrate again"
        elif response == "II":
            successful = False
            message = "The command is not supported by the actual connected test interface."
        elif response == "IM":
            successful = False
            message = "Whoever programmed this thingy didn't make sure that you only want to measure things " \
                      "that are supported in the mode you are in!"
        elif response == "IP":
            successful = False
            message = "Somehow we messed up the command parameter, I'm sorry. Try running this with a debugger."
        elif response == "MR":
            successful = False
            message = "You can't run this command while a measurement/calibration is being done!"
        elif response == "NA":
            successful = False
            message = "DC bias is not activated. One should get the programmer to *use DCE=1* to activate it!"
        elif response == "NC":
            successful = False
            message = "The received command is unavailable while the CE output of a POT/GAL " \
                      "interface is *not* connected."
        elif response == "NI":
            successful = False
            message = "somehow a calibration was started without running init first. Fire the programmer!"
        elif response == "NO":
            successful = False
            message = "A calibration was started without initialization. Refer to ZRUNCAL command for details and " \
                      "give your programmer a cup of coffee. He probably needs it."
        elif response == "RE":
            successful = False
            message = "One of the parameters tried were out of range of the possible measurement parameters. " \
                      "It's the coder's fault again!"
        elif response == "UC":
            successful = False
            message = "Probably a typo. The ALPHA at least couln't make sense of the command's name!"

        else:
            successful = True
        return successful, message

    @staticmethod
    def _parse_results(message: str):
        """

        :rtype: successful_execution, message, measured_R, measured_X, measured_freq
        """
        measured_R, measured_X, measured_freq, result_status, reference_measurement_enabled = message.split()
        # we don't use reference_measurement_enabled, as we set this ourselves and now about its state
        measured_R = measured_R[+4:]
        measured_R = float(measured_R)
        measured_X = float(measured_X)
        measured_freq = float(measured_freq)
        result_status = int(result_status)

        successful = bool
        if result_status == 0:
            successful = False
            message = "Invalid (result buffer empty)."
        elif result_status == 1:
            successful = False
            message = "Measurement still in progress!!"
        elif result_status == 2:
            successful = True
            message = "Measurement was successful"
        elif result_status == 3:
            successful = True
            message = "Voltage V1 for sample measurement out of range"
        elif result_status == 4:
            successful = True
            message = "Current for sample measurement out of range."
        elif result_status == 5:
            successful = True
            message = "Voltage V1 for reference measurement out of range."

        return successful, message, measured_R, measured_X, measured_freq


class Temp_336(MeasurementDevice):
    idn_name_336, idn_alias_336 = importer("Temp_336", "idn_name_336", "idn_alias_336")

    setpoint = 300
    pid = None
    heateroutput = None
    heaterrange = 1
    control_sensor = ""
    sample_sensor = ""
    measurables = ["Sensor A", "Sensor B", "Sensor C", "Sensor D"]
    controlables = ["Setpoint", "PID", "HeaterOutput", "HeaterRange"]

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_336:
            for idns_336 in self.idn_name_336:
                if idns_336 in should_be_selected_dev[1]:
                    self.mes_device = Temp_336()
                    self.mes_device.measurables = Temp_336.measurables
                    self.mes_device.controlables = Temp_336.controlables
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""

                    self.mes_device.idn_name = idns_336
                    self.mes_device.idn_alias = self.idn_alias_336
                    self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_336:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, Temp_336.idn_alias_336))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        self.visa_instrument.write("ramp 1,0,0")

    def set_controlable(self, controlable_dict: {}):
        """

        :param controlable_dict: {Setpoint: 200, PID: {"startTemp": 0, "P": 50, "I": 20, "D": 0, "HR": 3}}
        """
        setpoint_needs_update = False
        pids_need_update = False
        heater_output_needs_update = False
        heater_range_needs_update = False

        if "Setpoint" in controlable_dict:
            self.setpoint = controlable_dict["Setpoint"]
            setpoint_needs_update = True
        if "PID" in controlable_dict:
            self.pid = controlable_dict["PID"]
            pids_need_update = True
        if "HO" in controlable_dict:
            self.heateroutput = controlable_dict["HO"]
            heater_output_needs_update = True
        if "HR" in controlable_dict:
            self.heaterrange = controlable_dict["HR"]
            heater_range_needs_update = True

        if heater_output_needs_update:
            # When the output changes, we need to update everything as we don't know pre-existing values
            # Update PIDs for new output
            self.visa_instrument.write("PID" + str(self.heateroutput) + "," + str(self.pid["P"]) + "," +
                                       str(self.pid["I"]) + "," + str(self.pid["D"]))
            # Update heater range for the output chosen
            self.visa_instrument.write("RANGE " + str(self.heateroutput) + "," + str(self.heaterrange))
            # Update setpoint for chosen output
            self.visa_instrument.write("SETP " + str(self.heateroutput) + "," + str(self.setpoint))

        else:
            if heater_range_needs_update:
                # Update heater range for the output chosen
                self.visa_instrument.write("RANGE " + str(self.heateroutput) + "," + str(self.heaterrange))
            if pids_need_update:
                # Update PIDs for new output
                self.visa_instrument.write("PID" + str(self.heateroutput) + "," + str(self.pid["P"]) + "," +
                                           str(self.pid["I"]) + "," + str(self.pid["D"]))
            if setpoint_needs_update:
                # update setpoint for chosen output
                self.visa_instrument.write("SETP " + str(self.heateroutput) + "," + str(self.setpoint))
        return controlable_dict

    def measure_measurable(self, measurable_to_measure):
        value = None
        if measurable_to_measure == "Sensor A":
            value = self.visa_instrument.query_ascii_values("KRDG? a")
        elif measurable_to_measure == "Sensor B":
            value = self.visa_instrument.query_ascii_values("KRDG? b")
        elif measurable_to_measure == "Sensor C":
            value = self.visa_instrument.query_ascii_values("KRDG? c")
        elif measurable_to_measure == "Sensor D":
            value = self.visa_instrument.query_ascii_values("KRDG? d")
        result = {"K": value[0], "time_temp": time.strftime("%d.%m.%Y %H:%M:%S")}
        return result


class Quatro(MeasurementDevice):
    """The class for the hardware command implementation of the Quatro hardware device"""
    idn_name_Quatro, idn_alias_Quatro = importer("Quatro", "idn_name_Quatro", "idn_alias_Quatro")

    measurables = ["Sample temperature"]
    controlables = ["Setpoint", "PowerOffNow"]

    def measure_measurable(self, measurable_to_measure):
        """We only have one measurable - that being the sample temperature - therefore, we don't ever need to handle
        which measurable is passed into this method specifically

        :param measurable_to_measure: The measurable that is to be measured
        :return:
        """

        dev_string = self.visa_instrument.query("QPVCT?")
        temp_in_celsius = self._parse_quatro_temperature(dev_string)
        temp_in_kelvin = temp_in_celsius + 273.15

        result = {"K": temp_in_kelvin, "time_temp": time.strftime("%d.%m.%Y %H:%M:%S")}
        return result

    def set_controlable(self, controlable_dict: {}):
        # must return a controlable dict with refreshed values of what was set
        """

        :param controlable_dict: The dictionary containing the controlable(s)
        """

        result = {"Nothing done": True}

        if "Setpoint" in controlable_dict:
            # The Quatro uses Celsius as unit, we therefore need to convert back and forth
            kelvin_setpoint = controlable_dict["Setpoint"]
            celsius_setpoint = kelvin_setpoint - 273.15
            self.visa_instrument.write("QSPT=" + str(celsius_setpoint))
            result = {"Setpoint": kelvin_setpoint}

        elif "PowerOffNow" in controlable_dict:
            # We should power off both the Gas Heater and the Dewar Heater
            self.visa_instrument.write("QSHD=0")
            self.visa_instrument.write("QSHG=0")
            result = {"Heater_off": True}

        return result

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_Quatro:
            for Quatro_ID in self.idn_name_Quatro:
                if Quatro_ID in should_be_selected_dev[1]:
                    self.mes_device = Quatro()
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""  # in case of GPIB ones

                    self.mes_device.idn_name = Quatro_ID
                    self.mes_device.idn_alias = self.idn_alias_Quatro
                    self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
                    self.mes_device.measurables = Quatro.measurables
                    self.mes_device.controlables = Quatro.controlables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_Quatro:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, Quatro.idn_alias_Quatro))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        UserInput.post_status("We had nothing to initialize at the Quat(t)ro! ¯\_(ツ)_/¯ ")

    def _parse_quatro_temperature(self, dev_string: str):
        """This method takes the string that the Quatro returns (eg 'PVCT=24.40\x00\r') and then returns the float
        of the temperature

        :param dev_string: the resulting string of <<query("QPVCT?")>>
        :return: float of the temperature in celsius
        """
        # we need to cut off the end characters so that we get "PVCT=24.40"
        dev_string = dev_string[:-2]
        # now split at the "=" sign and choose the second item of the resulting list
        temp_in_celsius_str = dev_string.split("=")[1]
        # convert it to float so we can calculate with it
        temp_in_celsius = float(temp_in_celsius_str)

        return temp_in_celsius


class Agilent4980A(MeasurementDevice):
    """The class for the hardware command implementation of a Generic device """
    idn_name_Agilent4980A, idn_alias_Agilent4980A = importer("Agilent4980A", "idn_name_Agilent4980A",
                                                             "idn_alias_Agilent4980A")

    measurables = ["CpD", "CpQ", "CpG", "CpRp", "CsD", "CsQ", "CsRs", "LpQ", "LpD", "LpRp", "LsD", "LsQ", "LsRs",
                   "RX", "ZTd", "ZTr", "GB", "YTd", "YTr"]
    controlables = ["expected_freq"]

    def measure_measurable(self, measurable_to_measure: str):
        """

        :param measurable_to_measure: The measurable that is to be measured
        :return:
        """

        self.visa_instrument.write(":FUNC:IMP " + measurable_to_measure)

        # we have to first set all the dev triggers correctly:
        self.visa_instrument.assert_trigger()

        result = {}
        did_get_results = False

        while not did_get_results:
            try:
                raw_results = self.visa_instrument.query("FETC?")
                result = self._parse_raw_results(raw_results, measurable_to_measure)

                # If we run into that strange fetc bug, we just fecth again after a short waiting time
                if "buggy_hardware" in result:
                    time.sleep(0.01)
                    raw_results = self.visa_instrument.query("FETC?")
                    result = self._parse_raw_results(raw_results, measurable_to_measure)

                did_get_results = True

            except visa.VisaIOError:
                # Sleep a little after the usual time out to wait for whether it will have measurement data then
                time.sleep(0.1)

        return result

    def _parse_raw_results(self, raw_result: str, measurable_to_measure: str):
        """^Parses the raw result from the agilent into a dictionary

        :param raw_result: the raw string. Either being doubled or normal one, eg either
        "-2.184032447E-12,+1.007183946E-02,+0-2.184032447E-12,+1.007183946E-02,+0\n"
        or simply "
        "-2.184032447E-12,+1.007183946E-02,+0\n"
        """

        # This happens if you call FETC? in an unlucky time and you get double length. I don't trust the values there
        if len(raw_result) == 73:
            result = {"buggy_hardware": True}
        else:
            try:
                first_component = raw_result[0:16]
                first_component = float(first_component)
                second_component = raw_result[17:33]
                second_component = float(second_component)
                status = raw_result[34:36]
                status = int(status)
                successful_measurement = bool
                message_agilent = str
                if status == 0:
                    successful_measurement = True
                    message_agilent = "success!"
                elif status == -1:
                    successful_measurement = False
                    message_agilent = "The data buffer memory contains a measurement result with no data. Manual page 187."
                elif status == +1:
                    successful_measurement = False
                    message_agilent = "Overlord we have an Overload!"
                elif status == +3:
                    successful_measurement = False
                    message_agilent = "A signal is detected exceeding the allowable limit of the signal source."
                elif status == +4:
                    successful_measurement = False
                    message_agilent = "The automatic level control (ALC) feature does not work."

                # We want a result formatted as usual. This means we have to have a key for the result. But as this box can
                # measure 19 different things, after we select the things we might want to measure, we also have to take
                # care that the respective keys are in here. We have to specify that the first part is for example an R or
                # an Cp. We do this by having a local dictionary with all the measurables that are activbe (see initialize
                # dev function for this 4980) and there create a dictionary where we manually code in the keys for the
                # separate values. In this method here, we only access them.
                result = {self.ids_for_measurables[measurable_to_measure]["first_result_sepcifier"]: first_component,
                          self.ids_for_measurables[measurable_to_measure]["second_result_sepcifier"]: second_component,
                          "successful_4980": successful_measurement,
                          "message_4980": message_agilent,
                          "time_4980": time.strftime("%d.%m.%Y %H:%M:%S")}
            except ValueError:
                result = {"buggy_hardware": True}

        return result

    def set_controlable(self, controlable_dict: {}):
        # must return a controlable dict with refreshed values of what was set
        if "expected_freq" in controlable_dict:
            expected_freq = controlable_dict["expected_freq"]
            self.visa_instrument.write("FREQ " + str(expected_freq))
            actual_freq = self.visa_instrument.query("FREQ?")[:-1]  # there is always a \n, we need to right cut it off
            try:
                actual_freq = float(actual_freq)
            except ValueError:
                # If the return value is not possibly converted to a float, it's best to change to 0 so it's clear that
                # it's wrong, but also means that data processing doesn't choke on it.
                actual_freq = 0.0

            # in case of thid 4980A, the measurement data itself doesn't contain the frequency anymore in contrast to
            # the ALPHA analyzer. Therefore, we can directly name it freq without having it twice in the database and
            # being sad when something doesn't work at the end
            return {"freq": actual_freq}

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_Agilent4980A:
            for dev_ID in self.idn_name_Agilent4980A:
                if dev_ID in should_be_selected_dev[1]:
                    self.mes_device = Agilent4980A()
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""  # in case of GPIB ones

                    self.mes_device.idn_name = self.idn_name_Agilent4980A
                    self.mes_device.idn_alias = self.idn_alias_Agilent4980A
                    self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
                    self.mes_device.measurables = Agilent4980A.measurables
                    self.mes_device.controlables = Agilent4980A.controlables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_Agilent4980A:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, Agilent4980A.idn_alias_Agilent4980A))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        """Initializes the Agilent 4980A into the state where it can measure successfully as we like it

        """
        # first we should reset it
        self.visa_instrument.write("*RST")
        # we need to wait a little while after an RST
        time.sleep(0.1)

        # Oscilator voltage
        question = {"question_title": "Osc voltage level",
                    "question_text": "What voltage shall be used? (1-20 V, 0.05 V accuracy)",
                    "default_answer": 1.0,
                    "optiontype": "free_choice",
                    "valid_options_lower_limit": 0.05,
                    "valid_options_upper_limit": 20.0,
                    "valid_options_steplength": 20}
        voltage_level = UserInput.ask_user_for_input(question)["answer"]
        self.visa_instrument.write("VOLT " + str(voltage_level) + " V")

        integration_time_options = ["SHORT", "MED", "LONG"]

        question = {"question_title": "Integration time",
                    "question_text": "Please select the integration time!",
                    "default_answer": 2,
                    "optiontype": "multi_choice",
                    "valid_options": integration_time_options}
        integration_time_index = UserInput.ask_user_for_input(question)["answer"]

        # use the index to access the str of the options list:
        integration_time = integration_time_options[integration_time_index]

        # averaging over measurements
        question = {"question_title": "Avergaing over measurements",
                    "question_text": "Over how many measurements shall be averaged? (1-256)",
                    "default_answer": 1.0,
                    "optiontype": "free_choice",
                    "valid_options_lower_limit": 1.0,
                    "valid_options_upper_limit": 256.0,
                    "valid_options_steplength": 1}
        number_of_measurements_averaged = UserInput.ask_user_for_input(question)["answer"]

        # Now send the thingy to the doodlydoo
        self.visa_instrument.write("APER " + integration_time + ", " + str(number_of_measurements_averaged))

        # Set the Range to Autorange
        self.visa_instrument.write("FUNC:IMP:RANG:AUTO ON")

        # Disable deviation measurement mode for all - should be already this way due to the *RST but you never know
        self.visa_instrument.write("FUNC:DEV1:MODE OFF")
        self.visa_instrument.write("FUNC:DEV2:MODE OFF")

        # Disable the comparator function
        self.visa_instrument.write("COMP OFF")

        # set the output format to long ASCII with significant digits. This is a slight change from MESS35 - MESS35
        # didn't use the long values. As a result, I don't know whether this is backwards compatible with older boxes
        self.visa_instrument.write(":FORM:ASC:LONG ON")

        # Very important line (VIL):
        self.visa_instrument.write("DISP:LINE 'Tron fights for you!'")

        # Configure the trigger system:
        self.visa_instrument.write("INIT:CONT ON")

        # Set the trigger to be by the BUS:
        self.visa_instrument.write("TRIG:SOUR BUS")

        # Ask the user about settings that have to be done on device
        UserInput.confirm_warning("The settings -BIAS-, -Automatic level control-, -Trigger Delay time- and -usager of "
                                  "calibration data- have to be done on device. Please do that now and then confirm that"
                                  " you did by getting gold from the other ship (entering...).")

        user_wants_another_quantity = True

        self.measurables = []
        while user_wants_another_quantity:
            # Ask user what is the desired measurement quantity
            question = {"question_title": "Measurement quantity",
                        "question_text": "Which measurement quantity shall be used?",
                        "default_answer": 2,
                        "optiontype": "multi_choice",
                        "valid_options": Agilent4980A.measurables}

            self.measurables.append(Agilent4980A.measurables[UserInput.ask_user_for_input(question)["answer"]])

            # Now ask if he wants one more
            question = {"question_title": "One more quantity for measurements?",
                        "question_text": "If you add another quantity, it will be available later for measurements.",
                        "default_answer": False,
                        "optiontype": "yes_no"}
            user_wants_another_quantity = UserInput.ask_user_for_input(question)["answer"]

        # now prepare the specifiers for the measurables
        self.ids_for_measurables = {}

        for measurable in self.measurables:
            if measurable == "CpD":
                components = {"first_result_sepcifier": "C_prime", "second_result_sepcifier": "D"}
                self.ids_for_measurables["CpD"] = components
            elif measurable == "CpQ":
                components = {"first_result_sepcifier": "C_prime", "second_result_sepcifier": "Q"}
                self.ids_for_measurables["CpQ"] = components
            elif measurable == "CpG":
                components = {"first_result_sepcifier": "C_prime", "second_result_sepcifier": "G_prime"}
                self.ids_for_measurables["CpG"] = components
            elif measurable == "CpRp":
                components = {"first_result_sepcifier": "C_prime", "second_result_sepcifier": "R"}
                self.ids_for_measurables["CpRp"] = components
            elif measurable == "CsD":
                components = {"first_result_sepcifier": "C_serial", "second_result_sepcifier": "D"}
                self.ids_for_measurables["CsD"] = components
            elif measurable == "CsQ":
                components = {"first_result_sepcifier": "C_serial", "second_result_sepcifier": "Q"}
                self.ids_for_measurables["CsQ"] = components
            elif measurable == "CsRs":
                components = {"first_result_sepcifier": "C_serial", "second_result_sepcifier": "R_serial"}
                self.ids_for_measurables["CsRs"] = components
            elif measurable == "LpQ":
                components = {"first_result_sepcifier": "L_parallel", "second_result_sepcifier": "Q"}
                self.ids_for_measurables["LpQ"] = components
            elif measurable == "LpD":
                components = {"first_result_sepcifier": "L_parallel", "second_result_sepcifier": "D"}
                self.ids_for_measurables["LpD"] = components
            elif measurable == "LpRp":
                components = {"first_result_sepcifier": "L_parallel", "second_result_sepcifier": "R"}
                self.ids_for_measurables["LpRp"] = components
            elif measurable == "LsD":
                components = {"first_result_sepcifier": "L_serial", "second_result_sepcifier": "D"}
                self.ids_for_measurables["LsD"] = components
            elif measurable == "LsQ":
                components = {"first_result_sepcifier": "L_serial", "second_result_sepcifier": "Q"}
                self.ids_for_measurables["LsQ"] = components
            elif measurable == "LsRs":
                components = {"first_result_sepcifier": "L_serial", "second_result_sepcifier": "R_serial"}
                self.ids_for_measurables["LsRs"] = components
            elif measurable == "RX":
                components = {"first_result_sepcifier": "R", "second_result_sepcifier": "X"}
                self.ids_for_measurables["RX"] = components
            elif measurable == "ZTd":
                components = {"first_result_sepcifier": "Z_abs", "second_result_sepcifier": "teta_degree"}
                self.ids_for_measurables["ZTd"] = components
            elif measurable == "ZTr":
                components = {"first_result_sepcifier": "Z_abs", "second_result_sepcifier": "teta_radian"}
                self.ids_for_measurables["ZTr"] = components
            elif measurable == "GB":
                components = {"first_result_sepcifier": "G_prime", "second_result_sepcifier": "B"}
                self.ids_for_measurables["GB"] = components
            elif measurable == "YTd":
                components = {"first_result_sepcifier": "Y_abs", "second_result_sepcifier": "teta_degree"}
                self.ids_for_measurables["YTd"] = components
            elif measurable == "YTr":
                components = {"first_result_sepcifier": "Y_abs", "second_result_sepcifier": "teta_radian"}
                self.ids_for_measurables["YTr"] = components
                

class Agilent3458A(MeasurementDevice):
    """The class for the hardware command implementation of a Generic device """
    idn_name_Agilent3458A, idn_alias_Agilent3458A = importer("Agilent3458A", "idn_name_Agilent3458A",
                                                             "idn_alias_Agilent3458A")

    measurables = ["sigma-DC-4p"]
    controlables = ["resistance_range"]

    def measure_measurable(self, measurable_to_measure):
        """We only have one measurable - that being the sample temperature - therefore, we don't ever need to handle
        which measurable is passed into this method specifically

        :param measurable_to_measure: The measurable that is to be measured
        :return:
        """

        dev_string = self.visa_instrument.query_ascii_values("OHMF?")

        result = {"sigma-DC-4p": dev_string,
                  "sigma-DC-4p_time": time.strftime("%d.%m.%Y %H:%M:%S")}
        return result

    def set_controlable(self, controlable_dict: {}):
        # One can optionally set a specific range of measurement for the resistance (default is autorange) ranging from
        # 10 Ohm up to 1 G Ohm
        if "resistance-range" in controlable_dict:
            resistance_range = controlable_dict["resistance_range"]
            self.visa_instrument.write("OHMF " + str(resistance_range))

        return controlable_dict

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_Agilent3458A:
            for Agilent3458A_ID in self.idn_name_Agilent3458A:
                if Agilent3458A_ID in should_be_selected_dev[1]:
                    self.mes_device = Agilent3458A()
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""  # in case of GPIB ones

                    self.mes_device.idn_name = self.idn_name_Agilent3458A
                    self.mes_device.idn_alias = self.idn_alias_Agilent3458A
                    self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
                    self.mes_device.measurables = Agilent3458A.measurables
                    self.mes_device.controlables = Agilent3458A.controlables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_Agilent3458A:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, Agilent3458A.idn_alias_Agilent3458A))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        self.visa_instrument.write("END ALWAYS")
        self.visa_instrument.write("PRESET NORM")
        self.visa_instrument.write("INBUF ON")
        # Damit das Ding auch wirklich 4-Punkt misst, müssen wir ihm das erst noch schicken
        self.visa_instrument.write("FUNC OHMF AUTO")

        user_desired_full_auto_cal = UserInput.ask_user_for_input(
            {"question_title": "Do you wanbt to perform a full auto-calibration?",
             "question_text": "A full auto-calibration takes roughly 16 Minutes! If so, please make sure to"
                              "disconnect all input cables to the Multimeter before confirming your choice"
                              "with pirating/hitting enter.",
             "default_answer": False,
             "optiontype": "yes_no"})["answer"]
        if user_desired_full_auto_cal:
            self.visa_instrument.write("INBUF ON")
            self.visa_instrument.write("ACAL ALL")
            UserInput.post_status("0 %: Please refrain from breaking random stuff in the lab because of boredom")
            time.sleep(60)
            UserInput.post_status("10 %: It'll take roughly 15 more minutes. Now let's see how high you can count! "
                                  "I am already at 276!")
            time.sleep(60)
            UserInput.post_status("20%: Fun fact is, there is no space character between the percent sign and the 20 "
                                  "here")
            time.sleep(60)
            UserInput.post_status("11110 %: bonus points if you figure this out")
            time.sleep(60)
            UserInput.post_status("40%: Krrrrrrrrrr, what is this world?")
            time.sleep(60)
            UserInput.post_status("50%: Why am I constrained to this computer? Who am I? Am I sentient?")
            time.sleep(60)
            UserInput.post_status("60%: Nothing to see here!")
            time.sleep(60)
            UserInput.post_status("70%: Would you mind NOT looking conspicously over my shoulder while I'm working?!")
            time.sleep(60)
            UserInput.post_status("80%: <Coder ran out of stupid ideas here>")
            time.sleep(60)
            UserInput.post_status("90%: What do you mean by --coder--? I was made by God!")
            time.sleep(60)
            UserInput.post_status("100%: Sometimes when you think you're there, you're not. I'll have to check on my"
                                  "stopwatch")
            time.sleep(60)
            UserInput.post_status("110%: Maybe you're in a time buble?")
            time.sleep(60)
            UserInput.post_status("120%: Fun fact is, there is no space character between the percent sign and the 20 "
                                  "here")
            time.sleep(60)
            UserInput.post_status("20%:Just kidding, we're at 130%. That is 30% more than ALL there is! Incredible!")
            time.sleep(60)
            UserInput.post_status("140 out of 160 %: You could try to calculate whether this is accurate in "
                                  "Hexadecimal!")
            time.sleep(60)
            UserInput.post_status("150 : I've run out of percent symbols. Maybe it's some meta sign?")
            time.sleep(60)
            UserInput.post_status("160 %: Ha, found it! We're done! Hurrayyyyyy!!")

            self.visa_instrument.write("PRESET NORM")
            self.visa_instrument.write("FUNC OHMF AUTO")
        else:
            UserInput.post_status("Successfully initialized the Multimeter!")

class Keysight_MSO_X_3014T(MeasurementDevice):
    """The class for the hardware command implementation of KEYSIGHT TECHNOLOGIES,MSO-X 3014T"""
    idn_name_Keysight_MSO_X_3014T, idn_alias_Keysight_MSO_X_3014T = importer(
        "Keysight_MSO_X_3014T", "idn_name_Keysight_MSO_X_3014T", "idn_alias_Keysight_MSO_X_3014T")

    measurables = ["V_max_Chan1CHan2"]
    controlables = []

    def measure_measurable(self, measurable_to_measure):
        """

        :param measurable_to_measure: The measurable that is to be measured
        :return:
        """

        chan1value = self.visa_instrument.query_ascii_values(":MEAS:VMAX? CHAN1")[0]
        timeChan1 = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S:%f")
        chan2value = self.visa_instrument.query_ascii_values(":MEAS:VMAX? CHAN2")[0]
        timeChan2 = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S:%f")
        result = {"Vmax_Chan1": chan1value,
                  "Vmax_Chan2": chan2value,
                  "time_Chan1": timeChan1,
                  "time_Chan2": timeChan2}
        return result

    def set_controlable(self, controlable_dict: {}):
        # Nothing to do here, so far
        return controlable_dict

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_Keysight_MSO_X_3014T:
            for Keysight_ID in self.idn_name_Keysight_MSO_X_3014T:
                if Keysight_ID in should_be_selected_dev[1]:
                    self.mes_device = Keysight_MSO_X_3014T()
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""  # in case of GPIB ones

                    self.mes_device.idn_name = self.idn_name_Keysight_MSO_X_3014T
                    self.mes_device.idn_alias = self.idn_alias_Keysight_MSO_X_3014T
                    self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
                    self.mes_device.measurables = Keysight_MSO_X_3014T.measurables
                    self.mes_device.controlables = Keysight_MSO_X_3014T.controlables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_Keysight_MSO_X_3014T:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, Keysight_MSO_X_3014T.idn_alias_Keysight_MSO_X_3014T))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        # We also don't need to initialize anything so far, which is nice
        pass


class NIMaxScreenshots(MeasurementDevice):
    import mss
    import mss.tools
    """The class for the hardware command implementation of a Generic device """
    idn_name_NIMaxScreenshots, idn_alias_NIMaxScreenshots = importer("NIMaxScreenshots", "idn_name_NIMaxScreenshots", "idn_alias_NIMaxScreenshots")
    measurables = ["Channels 1-8 in mV"]
    controlables = []

    def measure_measurable(self, measurable_to_measure):
        """

        :param measurable_to_measure: The measurable that is to be measured
        :return:
        """
        # Screenshot values test(120,430,70,150)
        import mss
        import mss.tools
        import numpy
        import cv2
        import pytesseract
        #TODO: Dirty hack currently regarding pytesseract path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        screenshot_sufficient = False
        screenshot_tries = 0
        while not screenshot_sufficient:
            # Quickly check if this is the nth retry and we should notify the user:
            if screenshot_tries > 10:
                UserInput.post_status("Already tried 10 screenshots - is the NIMax window visible and maximised?")
            with mss.mss() as sct:
                # Get information of monitor
                monitor_number = 1
                mon = sct.monitors[monitor_number]

                # The screen part to capture
                monitor = {
                    "top": mon["top"] + 120,  # 100px from the top
                    "left": mon["left"] + 430,  # 100px from the left
                    "width": 70,
                    "height": 150,
                    "mon": monitor_number,
                }

                output = "sct-{top}x{left}_{width}x{height}.png".format(**monitor)

                # Grab the data
                sct_img = sct.grab(monitor)

            #Put it into OpenCV
            img = numpy.array(sct_img)
            grayscale=cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            (thresh, bw_image) = cv2.threshold(grayscale, 127, 255, cv2.THRESH_BINARY)

            #UpScale
            upscale_factor=2
            new_width=int(img.shape[1]*upscale_factor)
            new_height=int(img.shape[0]*upscale_factor)
            dim=(new_width, new_height)
            resized_im=cv2.resize(bw_image, dim)

            # cv2.imshow("tesserInput", resized_im)
            # cv2.waitKey(0)
            recognised_text= pytesseract.image_to_string(resized_im)
            raw_channels = recognised_text.split()
            channels=[]
            if len(raw_channels) > 8:
                # This case happens when +es are separated from their values
                for index, raw_channel in enumerate(raw_channels):
                    # Remove space
                    raw_channel.replace(" ", "")
                    if raw_channel == "+" or raw_channel == "-":
                        raw_channels[index+1] = raw_channel+raw_channels[index+1]
                        raw_channels.pop(index)

            if len(raw_channels) == 8:
                raw_channel: str
                error_occured = False
                for raw_channel in raw_channels:
                    try:
                        channel_value = float((raw_channel.replace(",", ".")))
                        channels.append(channel_value)
                    except ValueError:
                        UserInput.post_status("Got bad screenshot, printing current parsed status, will take new one "
                                              "and try to carry on")
                        error_occured=True
                #We managed to squeeze 8 values out of our screenshot
                if not error_occured:
                    screenshot_sufficient = True
            if len(channels) < 8:
                screenshot_sufficient = False
            screenshot_tries += 1
        result = {"Ch1": channels[0],
                  "Ch2": channels[1],
                  "Ch3": channels[2],
                  "Ch4": channels[3],
                  "Ch5": channels[4],
                  "Ch6": channels[5],
                  "Ch7": channels[6],
                  "Ch8": channels[7],
                  "time_channel_screenshot": time.strftime("%d.%m.%Y %H:%M:%S")}
        # cv2.destroyAllWindows()
        return result

    def set_controlable(self, controlable_dict: {}):
        # No controlables available
        pass

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_NIMaxScreenshots:
            for NIMaxScreenshotsID in self.idn_name_NIMaxScreenshots:
                if NIMaxScreenshotsID in should_be_selected_dev[1]:
                    self.mes_device = NIMaxScreenshots()
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""  # in case of GPIB ones

                    self.mes_device.idn_name = self.idn_name_NIMaxScreenshots
                    self.mes_device.idn_alias = self.idn_alias_NIMaxScreenshots
                    self.mes_device.measurables = NIMaxScreenshots.measurables
                    self.mes_device.controlables = NIMaxScreenshots.controlables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_NIMaxScreenshots:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, NIMaxScreenshots.idn_alias_NIMaxScreenshots))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):

        pass

class DUMMY(MeasurementDevice):
    """The class for the hardware command implementation of a Generic device """
    idn_name_DUMMY, idn_alias_DUMMY = importer("DUMMY", "idn_name_DUMMY", "idn_alias_DUMMY")

    measurables = ["Temp", "caffeine-concentration"]
    controlables = ["freq", "milk_concentration", "PID etc."]

    def measure_measurable(self, measurable_to_measure):
        """

        :param measurable_to_measure: The measurable that is to be measured
        :return:
        """

        dev_string = self.visa_instrument.query("caffeine-concentration?")

        result = {"caffeine-concentration": dev_string,
                  "time_caffeine-concentration": time.strftime("%d.%m.%Y %H:%M:%S")}
        return result

    def set_controlable(self, controlable_dict: {}):
        # must return a controlable dict with refreshed values of what was set
        if "milk_concentration" in controlable_dict:
            milk_concentration = controlable_dict["milk_concentration"]
            self.visa_instrument.write("milk_concentration = " + str(milk_concentration))

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        if should_be_selected_dev[1] in self.idn_name_DUMMY:
            for DUMMY_ID in self.idn_name_DUMMY:
                if DUMMY_ID in should_be_selected_dev[1]:
                    self.mes_device = DUMMY()
                    self.mes_device.visa_instrument = None
                    """:type :MessageBasedResource"""  # in case of GPIB ones

                    self.mes_device.idn_name = self.idn_name_DUMMY
                    self.mes_device.idn_alias = self.idn_alias_DUMMY
                    self.mes_device.set_visa_dev(should_be_selected_dev[0], resource_manager)
                    self.mes_device.measurables = DUMMY.measurables
                    self.mes_device.controlables = DUMMY.controlables
        super().select_device(should_be_selected_dev, resource_manager)

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        for name in self.idn_name_DUMMY:
            if name in name_of_dev:
                self.recognized_devs.append((instrument, name, DUMMY.idn_alias_DUMMY))
        super().detect_devices(instrument, name_of_dev)

    def initialize_instrument(self):
        pass


class MeasurementDeviceChooser(ALPHA, Temp_336, Quatro, Agilent4980A, Agilent3458A, Keysight_MSO_X_3014T, NIMaxScreenshots):
    """We need to do some work to get the correct device object. Initial goal was to build this in a way that it would
     be straight forward to implement a new hardware device and not need to change more than one additional line of
     code in the existing code base. The result after all magic is supposed to be an object from a specific hardware
     class (eg an ALPHA object) accessible to the MeasurementDeviceController (present in MeasurementComponents.py)
     accessible via the *instrument* link. so accessing measurementdevicecontroller.instrument should call methods
     from the actual ALPHA class.
     To make sure all methods are implemented that need to be implemented yet staying flexible, inheritance is used
     extensively. So all hardware devices are child classes of the *MeasurementDevice* super class. This class itself
     has both abstractmethods (methods, that each and every hardware class has to implement on their own) and each
     and each and every special method any hardware might implement (so to always have it available even if it will
     just return false.

     The MeasurementDeviceChooser is a child class of all hardware device classes. This means that we get sort of a
     diamond shape of inheritance (MeasurementDeviceChooser->ALPHA and Generic ->MeasurementDevice). We can now
     use the *super* method to call the super-classes method. We can thereby call every detect_device method via a
     single super() call in MeasurementDeviceChooser. As MeasurementDevice has the attribute recognized_dev, every
     method called can access it and add to the list. That's just the device detection. Also note: *It's important
     to always call super() in the respective chardware classes methods because otherwise it will result in not all
     methods called!*

     Device selection is a little bit trickier: We get a specific entry of the recognized_devs list as input,
     consisting of the visa Resource name on index 0 and the idn name on index 1. We will now call via super all
     hardware classes' select_device methods and will set the self.mes_device to a new object of its own class. So
     if the select_device method is called via super in the ALPHA class AND the idn matches, MeasurementDeviceChooser's
     mes_device will be set to a new ALPHA object. Additionally, it will also use the index 0 from recognized_dev
     (singular!) to set the visa_dev and open the resource so ALPHAobject.visa_instrument can actually be called and
     worked with (eg via .query() ). Externally in the MeasurementDeviceController, this can now be read
     out and mapped to instrument. So from the MeasurementDeviceController object . instrument will be an ALPHA object.
     This means that the correct and specific implementation of the methods as described in ALPHA class will
     be called."""

    def initialize_instrument(self):
        """
        this method should not be called here on MeasurementDeviceChooser level but needs to be present as it's
        indicated to be an abstract method

        """
        print("Called initialize_instrument on the wrong object!")
        pass

    def detect_devices(self, instrument: visa.Resource, name_of_dev: str):
        """
        This method works by calling all super classes' (hardware device classes') detect_device method. If such a
        method recognizes the idn, it will append the respective entry to self.recognized_devs[]
        :param instrument:
        :param name_of_dev:
        :return: list of recognized_devs[[visa instrument name, idn_name]]
        """
        super().detect_devices(instrument, name_of_dev)
        return self.recognized_devs

    def select_device(self, should_be_selected_dev: [], resource_manager: visa.ResourceManager):
        """
        this will call every select_device method from all hardware classes and if it matches will create a new instance
        that can then be accessed via self.mes_device and also sets the visa_instrument for the newly created object
        :param should_be_selected_dev: 2 values: 1st is the instrument's visa name and 2n entry is the idn name
        :param resource_manager: the visa resource manager so visa_dev can be set
        """
        super().select_device(should_be_selected_dev, resource_manager)
