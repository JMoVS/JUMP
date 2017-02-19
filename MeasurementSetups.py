"""Here we describe and implement the measurement setups, eg Coldhoead..."""
__copyright__ = "Copyright 2015 - 2016, Justin Scholz"
__author__ = "Justin Scholz"

from abc import ABCMeta, abstractmethod
from MeasurementHardware import MeasurementDeviceController
import visa
import UserInput


class MeasurementSetup(metaclass=ABCMeta):
    """The metaclass that hols all values and methods each individual measurement setup will adhere to"""

    # Same game as for MeasurementHardware. We want easy bolt-on of setups here, so we do the trickery with inheritance
    # for this, we have a setup thingy.

    def __init__(self):
        self.dev_resource_manager = visa.ResourceManager()
        self.list_of_setups = []
        self.setup = None
        self.controlables = []
        self.measurables = []

    @abstractmethod
    def list_available_setups(self):
        return

    @abstractmethod
    def select_setup(self, to_be_selected_setups_name: str):
        return

    @abstractmethod
    def change_value_of_controlable_to(self, controlable, new_value):
        """
            If a measurement setup has 2 controlables, depending on the one set, you can change different things. The
            temperature controller will call to this method everytime a new setpoint is wanted. Then the oven-setup
            can change state of the temperature controller so it can have different outputs or different PIDs etc
        :param controlable: the controlable we are talking about. Usually, it's gonna be temperature
        :param new_value: the new value for the controlable
        :return:
        """
        return controlable

    @abstractmethod
    def get_measurables(self):
        return

    @abstractmethod
    def get_controlables(self):
        return

    @abstractmethod
    def measure_measurable(self, measurable: dict):
        """
        In case some other stuff should get done before acquisition of measurable is done. Get's called before actual
        measurement device get's asked for the measurable
        :param mdc_for_measurable: the associated devices ms
        :param measurable: adhering to standards, it's eg freq_response, temp or sth like that.
        :return:
        """
        return

    @abstractmethod
    def _add_measurement_device_controllers(self):
        return

    @abstractmethod
    def init_after_creation(self):
        return

    @abstractmethod
    def get_limits(self):
        return

    @abstractmethod
    def measurement_done(self):
        return


class GLaDOS(MeasurementSetup):
    name_coldheadnew = "TKKG : Transportlaborkaltkopf GLaDOS (GLaDOS)"
    min_setpoint = 0
    max_setpoint = 500

    # I cannot provide the PID values of our setup, these are made up ones.
    PIDs = [{"startTemp": 0, "PID": {"P": 20, "I": 40, "D": 0}, "HR": 3, "HO": 1},
            {"startTemp": 200, "PID": {"P": 30, "I": 60, "D": 1}, "HR": 2, "HO": 1}]

    # On rather old hardware, the PID values were different depending on the temperature controller, to accomodate this,
    # one can provide old_PIDs. The temperature controllers themselves know whether they need to respect old or new PIDs

    old_controller_PIDS = [
        {"startTemp": 0, "old_PID": {"old_P": 10, "old_I": 20, "old_D": 30}, "old_HR": 3, "old_HO": 1},
        {"startTemp": 100, "old_PID": {"old_P": 20, "old_I": 30, "old_D": 0}, "old_HR": 3, "old_HO": 1},
        {"startTemp": 475, "old_PID": {"old_P": 30, "old_I": 20, "old_D": 10}, "old_HR": 3, "old_HO": 1}]

    # If you want to support more than 2 measurement devices at this setup, make sure to make this a list etc.

    mdc_for_temp_controller = None  # type: MeasurementDeviceController
    mdc_for_meas_device = None  # type: MeasurementDeviceController

    heater_output = ""

    def __init__(self):
        super().__init__()
        self.current_PID = {}
        self.current_old_PID = {}

    def get_limits(self):
        return [GLaDOS.min_setpoint, GLaDOS.max_setpoint]

    def measurement_done(self):
        pass  # at GLADOS, there is nothing to be done here, look at QUATRO as an example for when this is relevant

    def init_after_creation(self):
        self._add_measurement_device_controllers()
        self._set_sensors_temp_controller()
        self._generate_controlables_from_devices()
        self._generate_measurables()

    def _add_measurement_device_controllers(self):
        if not self.mdc_for_meas_device:
            UserInput.confirm_warning("Please select the MEASUREMENT device out of the list")
            self.mdc_for_meas_device = MeasurementDeviceController(self.dev_resource_manager)
        if not self.mdc_for_temp_controller:
            UserInput.confirm_warning("Please choose the TEMPERATURE controller out of the device list")
            self.mdc_for_temp_controller = MeasurementDeviceController(self.dev_resource_manager)

    def _generate_controlables_from_devices(self):
        """Generate all currently available controlables with the connected devices

        """
        self.controlables.append({"dev": self.mdc_for_temp_controller, "name": "Setpoint"})

        for dev_controlable in self.mdc_for_meas_device.controlables:
            controlable = {"dev": self.mdc_for_meas_device, "name": dev_controlable}
            self.controlables.append(controlable)

    def _generate_measurables(self):

        """Generate all currently available measurables with the connected devices
        A measurable consists of a dictionary with the keys "dev" and "name", dev being an ms pointer and name a string

        """
        # Sample sensor and control sensor are the measurables, we don't particularly care about whether it's a,b,c or d
        self.measurables.append({"dev": self.mdc_for_temp_controller, "name": "Control Sensor"})
        self.measurables.append({"dev": self.mdc_for_temp_controller, "name": "Sample Sensor"})
        for dev_measurable in self.mdc_for_meas_device.measurables:
            measurable = {"dev": self.mdc_for_meas_device, "name": dev_measurable}
            self.measurables.append(measurable)

    def get_measurables(self):
        return self.measurables

    def get_controlables(self):
        return self.controlables

    def list_available_setups(self):
        self.list_of_setups.append(self.name_coldheadnew)
        super().list_available_setups()

    def select_setup(self, to_be_selected_setups_name: str):
        if self.name_coldheadnew == to_be_selected_setups_name:
            self.setup = GLaDOS()
        super().select_setup(to_be_selected_setups_name)

    def change_value_of_controlable_to(self, controlable, new_value):
        """As all talking is done through a measurement setup, this is how you communicate to the device

        :param controlable:
        :type controlable: dict
        :param new_value:
        """

        # If the controlable's name is "setpoint", we have to make sure that we don't exceed setup limits
        # as well as that we set PIDs correctly
        new_controlable = controlable
        if controlable["name"] == "Setpoint":
            # we have to enumerate to make sure get the correct PID. For this, we have to check the next item whether
            # it is exactly in range or not. We can safely send a temperature controller PIDs as well as old_PIDs as the
            # temperature controller determines whether he uses old ones or current ones
            for index, item in enumerate(self.PIDs):
                # first check whether it is bigger than the start_temp of the item
                if new_value >= item["startTemp"]:
                    # then check whether current value is lower than the start value of the next one, if yes, then bingo
                    if new_value < self.PIDs[index + 1]["startTemp"]:
                        # we only send the PIDs if they changed:
                        if self.current_PID != item:
                            new_controlable = controlable["dev"].set_controlable(item)
                            self.current_PID = item
                        break
            # So after sending new PIDs that might get ignored by the temperature controller because it's an old one,
            # we quickly iterate over all the old ones as well
            for index, item in enumerate(self.old_controller_PIDS):
                # first check whether it is bigger than the start_temp of the item
                if new_value >= item["startTemp"]:
                    # then check whether current value is lower than the start value of the next one, if yes, then bingo
                    if new_value < self.old_controller_PIDS[index + 1]["startTemp"]:
                        # we only send the PIDs if they changed:
                        if self.current_old_PID != item:
                            new_controlable = controlable["dev"].set_controlable(item)
                            self.current_old_PID = item
                        break
            # Now, all PIDs are set correctly and therefore we can set a setpoint as needed and as allowed or not
            if self.min_setpoint <= new_value <= self.max_setpoint:
                new_controlable = controlable["dev"].set_controlable({"Setpoint": new_value})
            else:
                UserInput.confirm_warning("Your desired setpoint is above the setup's maximum, sry!")
        else:
            # Now here, we send the dev_controlable to the mdc. So eg {"applied_freq": 10} to the Alpha
            new_controlable = controlable["dev"].set_controlable({controlable["name"]: new_value})

        return new_controlable

    def measure_measurable(self, measurable: dict):
        # In the TKKG setup, we don't need to do anything specific before we read out the temperature or measure a
        # frequency at the ALPHA
        # As the measurable dict passed in here is in the format of: {"dev":PointerToDevMDC, "name":"measurable_name"}
        # But the device actually wants a simple string specifying the measurable, we have to create it
        # And as we defined "control sensor" and "sample sensor measurables on the measurementsetup level, we have to
        # account for that so useful data gets passed down

        local_measurable = measurable.copy()

        specifier = ""
        if local_measurable["name"] == "Sample Sensor":
            specifier = local_measurable["name"]
            local_measurable["name"] = self.sample_sensor
        elif local_measurable["name"] == "Control Sensor":
            specifier = local_measurable["name"]
            local_measurable["name"] = self.control_sensor
        datapoint = local_measurable["dev"].measure_measurable(local_measurable["name"])
        new_result = datapoint
        if "K" in datapoint:
            # We want to know which sensor was measured and as the temperature controller is unaware of the concept of
            # a control sensor and a sample sensor (that is only in MeasurementSetup), we have to catch that here
            new_result = {specifier: datapoint["K"]}
            if "time_temp" in datapoint:
                str_for_time_with_specifier = "time_" + specifier
                new_result[str_for_time_with_specifier] = datapoint["time_temp"]
        return new_result

    def _set_sensors_temp_controller(self):
        sensors = self.mdc_for_temp_controller.measurables
        question = {"question_title": "Control Sensor",
                    "question_text": "Which one of the measurables shall be your control sensor?",
                    "default_answer": 0,
                    "optiontype": "multi_choice",
                    "valid_options": sensors}
        answer = UserInput.ask_user_for_input(question)["answer"]
        self.control_sensor = sensors[answer]

        question = {"question_title": "Sample Sensor",
                    "question_text": "Which one of the measurables shall be your sample sensor?",
                    "default_answer": 0,
                    "optiontype": "multi_choice",
                    "valid_options": sensors}
        answer = UserInput.ask_user_for_input(question)["answer"]
        self.sample_sensor = sensors[answer]


class Quatro(MeasurementSetup):
    name_Quatro = "Quatro"
    min_setpoint = 0
    max_setpoint = 600

    current_start_temp = 0

    mdc_for_temp_controller = None  # type: MeasurementDeviceController
    mdc_for_meas_device = None  # type: MeasurementDeviceController

    Quatro_should_turn_off_after_measurement = True  # Initializes the value that is important for when the measurement

    # is finished.

    def init_after_creation(self):
        self._add_measurement_device_controllers()
        self._generate_controlables_from_devices()
        self._generate_measurables()
        self._should_Quatro_turn_off()

    def get_controlables(self):
        return self.controlables

    def get_limits(self):
        return [Quatro.min_setpoint, Quatro.max_setpoint]

    def measurement_done(self):
        if self.Quatro_should_turn_off_after_measurement:
            self.mdc_for_temp_controller.set_controlable({"PowerOffNow": True})

    def _add_measurement_device_controllers(self):
        if not self.mdc_for_temp_controller:
            UserInput.confirm_warning("Please select the QUATRO out of the device list!")
            self.mdc_for_temp_controller = MeasurementDeviceController(self.dev_resource_manager)
        if not self.mdc_for_meas_device:
            UserInput.confirm_warning("Please select the MEASUREMENT device out of the list")
            self.mdc_for_meas_device = MeasurementDeviceController(self.dev_resource_manager)

    def get_measurables(self):
        return self.measurables

    def change_value_of_controlable_to(self, controlable: dict, new_value):
        new_controlable = controlable["dev"].set_controlable({controlable["name"]: new_value})
        return new_controlable

    def measure_measurable(self, measurable):
        datapoint = measurable["dev"].measure_measurable(measurable["name"])
        return datapoint

    def list_available_setups(self):
        self.list_of_setups.append(self.name_Quatro)
        super().list_available_setups()

    def select_setup(self, to_be_selected_setups_name: str):
        if self.name_Quatro == to_be_selected_setups_name:
            self.setup = Quatro()
        super().select_setup(to_be_selected_setups_name)

    def _generate_controlables_from_devices(self):

        """Generate/ask all the devices what controlables are available

        """

        # Get the controlables of the measurement device
        for dev_controlable in self.mdc_for_meas_device.controlables:
            controlable = {"dev": self.mdc_for_meas_device, "name": dev_controlable}
            self.controlables.append(controlable)
        # Get the controlables of the temperature device (in the case of the Quatro, it will always be a Quatro)
        controlable = {"dev": self.mdc_for_temp_controller, "name": "Setpoint"}
        self.controlables.append(controlable)

    def _generate_measurables(self):
        self.measurables.append({"dev": self.mdc_for_temp_controller, "name": "Sample Sensor"})
        for dev_measurable in self.mdc_for_meas_device.measurables:
            measurable = {"dev": self.mdc_for_meas_device, "name": dev_measurable}
            self.measurables.append(measurable)

    def _should_Quatro_turn_off(self):
        question = {"question_title": "Heaters after measurement",
                    "question_text": "Should the Quatro's heaters (Dewar and Gas) be powered off when the measurement "
                                     "is finished?",
                    "default_answer": True,
                    "optiontype": "yes_no"}
        self.Quatro_should_turn_off_after_measurement = UserInput.ask_user_for_input(question)


class DUMMY(MeasurementSetup):
    name_DUMMY = "DUMMY"
    min_setpoint = 0
    max_setpoint = 475

    PIDs = [{"startTemp": 0, "PID": {"P": 40, "I": 20, "D": 0}, "HR": 3, "HO": 1},
            {"startTemp": 100, "PID": {"P": 50, "I": 20, "D": 0}, "HR": 3, "HO": 1},
            {"startTemp": 150, "PID": {"P": 50, "I": 20, "D": 0}, "HR": 3, "HO": 1}]

    old_controller_PIDS = [{"startTemp": 0, "PID": {"old_P": 50, "old_I": 20, "old_D": 0}, "old_HR": 3, "old_HO": 1},
                           {"startTemp": 100, "PID": {"old_P": 50, "old_I": 20, "old_D": 0}, "old_HR": 3, "old_HO": 1},
                           {"startTemp": 150, "PID": {"old_P": 50, "old_I": 20, "old_D": 0}, "old_HR": 3, "old_HO": 1}]

    current_start_temp = 0

    mdc_for_temp_controller = None
    mdc_for_meas_device = None

    def measurement_done(self):
        pass

    def get_limits(self):
        pass

    def init_after_creation(self):
        pass

    def get_controlables(self):
        pass

    def _add_measurement_device_controllers(self):
        pass

    def get_measurables(self):
        pass

    def change_value_of_controlable_to(self, controlable, new_value):
        pass

    def measure_measurable(self, measurable):
        pass

    def list_available_setups(self):
        self.list_of_setups.append(self.name_DUMMY)
        super().list_available_setups()

    def select_setup(self, to_be_selected_setups_name: str):
        if self.name_DUMMY == to_be_selected_setups_name:
            self.setup = DUMMY()
        super().select_setup(to_be_selected_setups_name)


class Generic(MeasurementSetup):
    name_Generic = "Generic"

    mdc1 = None  # type: MeasurementDeviceController
    mdc2 = None  # type: MeasurementDeviceController
    mdc3 = None  # type: MeasurementDeviceController
    mdc4 = None  # type: MeasurementDeviceController
    mdc5 = None  # type: MeasurementDeviceController

    def measurement_done(self):
        pass

    def get_limits(self):
        return ["No known limits to this Generic measurement setup"]

    def init_after_creation(self):
        self._add_measurement_device_controllers()
        self._generate_controlables_from_devices()
        self._generate_measurables()

    def get_controlables(self):
        return self.controlables

    def _add_measurement_device_controllers(self):
        """ We need to create the measurement device controllers. And we do this by literally creating them, as the init
        method of MeasurementDeviceController takes care of the actual "select device" and init stuff.

        """
        if not self.mdc1:
            UserInput.confirm_warning("Please select the 1st device out of the list")
            self.mdc1 = MeasurementDeviceController(self.dev_resource_manager)

        # We now have the first (and possibly only) mdc. If the user wants a second, he can now create it...
        user_wants_second_device = UserInput.ask_user_for_input({"question_title": "Add another device?",
                                                                 "question_text": "Do you want to configure a 2nd"
                                                                                  "device for use?",
                                                                 "default_answer": True,
                                                                 "optiontype": "yes_no"})["answer"]
        if user_wants_second_device and not self.mdc2:
            UserInput.confirm_warning("Please select the 2nd device out of the list")
            self.mdc2 = MeasurementDeviceController(self.dev_resource_manager)

        user_wants_third_device = UserInput.ask_user_for_input({"question_title": "Add another device?",
                                                                 "question_text": "Do you want to configure a 3rd"
                                                                                  "device for use?",
                                                                 "default_answer": False,
                                                                 "optiontype": "yes_no"})["answer"]
        if user_wants_third_device and not self.mdc3:
            UserInput.confirm_warning("Please select the 3rd device out of the list")
            self.mdc3 = MeasurementDeviceController(self.dev_resource_manager)

        user_wants_fourth_device = UserInput.ask_user_for_input({"question_title": "Add another device?",
                                                                 "question_text": "Do you want to configure a 4th"
                                                                                  "device for use?",
                                                                 "default_answer": False,
                                                                 "optiontype": "yes_no"})["answer"]
        if user_wants_fourth_device and not self.mdc4:
            UserInput.confirm_warning("Please select the 4th device out of the list")
            self.mdc4 = MeasurementDeviceController(self.dev_resource_manager)

        user_wants_third_device = UserInput.ask_user_for_input({"question_title": "Add another device?",
                                                                 "question_text": "Do you want to configure a 5th"
                                                                                  "device for use?",
                                                                 "default_answer": False,
                                                                 "optiontype": "yes_no"})["answer"]
        if user_wants_third_device and not self.mdc5:
            UserInput.confirm_warning("Please select the 5th device out of the list")
            self.mdc5 = MeasurementDeviceController(self.dev_resource_manager)

    def get_measurables(self):
        return self.measurables

    def change_value_of_controlable_to(self, controlable, new_value):
        return controlable["dev"].set_controlable({controlable["name"]: new_value})

    def measure_measurable(self, measurable):
        return measurable["dev"].measure_measurable(measurable["name"])

    def list_available_setups(self):
        self.list_of_setups.append(self.name_Generic)
        super().list_available_setups()

    def select_setup(self, to_be_selected_setups_name: str):
        if self.name_Generic == to_be_selected_setups_name:
            self.setup = Generic()
        super().select_setup(to_be_selected_setups_name)

    def _generate_controlables_from_devices(self):
        for dev_controlable in self.mdc1.controlables:
            controlable = {"dev": self.mdc1, "name": dev_controlable}
            self.controlables.append(controlable)
        if self.mdc2:
            for dev_controlable in self.mdc2.controlables:
                controlable = {"dev": self.mdc2, "name": dev_controlable}
                self.controlables.append(controlable)
            if self.mdc3:
                for dev_controlable in self.mdc3.controlables:
                    controlable = {"dev": self.mdc3, "name": dev_controlable}
                    self.controlables.append(controlable)
                if self.mdc4:
                    for dev_controlable in self.mdc4.controlables:
                        controlable = {"dev": self.mdc4, "name": dev_controlable}
                        self.controlables.append(controlable)
                    if self.mdc5:
                        for dev_controlable in self.mdc5.controlables:
                            controlable = {"dev": self.mdc5, "name": dev_controlable}
                            self.controlables.append(controlable)

    def _generate_measurables(self):
        for dev_measurable in self.mdc1.measurables:
            measurable = {"dev": self.mdc1, "name": dev_measurable}
            self.measurables.append(measurable)
        if self.mdc2:
            for dev_measurable in self.mdc2.measurables:
                measurable = {"dev": self.mdc2, "name": dev_measurable}
                self.measurables.append(measurable)
            if self.mdc3:
                for dev_measurable in self.mdc3.measurables:
                    measurable = {"dev": self.mdc3, "name": dev_measurable}
                    self.measurables.append(measurable)
                if self.mdc4:
                    for dev_measurable in self.mdc4.measurables:
                        measurable = {"dev": self.mdc4, "name": dev_measurable}
                        self.measurables.append(measurable)
                    if self.mdc5:
                        for dev_measurable in self.mdc5.measurables:
                            measurable = {"dev": self.mdc5, "name": dev_measurable}
                            self.measurables.append(measurable)


class MeasurementSetupHelper(GLaDOS, Quatro, Generic, DUMMY):
    def select_setup(self, to_be_selected_setups_name: str):
        """

        :rtype: MeasurementSetup
        """
        super().select_setup(to_be_selected_setups_name)
        return self.setup

    def list_available_setups(self):
        super().list_available_setups()
        return self.list_of_setups
