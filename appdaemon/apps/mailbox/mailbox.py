import appdaemon.plugins.hass.hassapi as hass
import datetime
import time
import globals
from globals import PEOPLE

class Mailbox(hass.Hass):

    def initialize(self):

        self.door_sensor = self.args["mail_door_sensor"]
        self.slot_sensor = self.args["mail_slot_sensor"]
        self.mail_sensor = self.args["mail_sensor"]
        self.state = self.get_state(self.mail_sensor)
        
        self.start_quiet = globals.notification_mode["start_quiet_weekday"]
        self.stop_quiet = globals.notification_mode["stop_quiet_weekday"]

        self.isa = self.get_state(PEOPLE['Isa']['device_tracker'])
        self.stefan = self.get_state(PEOPLE['Stefan']['device_tracker'])

        self.newState = ""
        self.attributes = {}      
        self.just_opened_door = False
        self.just_notified = False

        self.listen_state(self.just_opened, self.args["door"])
        if (self.state is None or self.state == ""):
            self.make_sensor()

        if "mail_slot_sensor" in self.args:
            self.listen_state(self.mailbox_opened, self.slot_sensor)
        if "mail_door_sensor" in self.args:
            self.listen_state(self.mailbox_opened, self.door_sensor)
 
    def just_opened(self, entity, attribute, old, new, kwargs):
        if (new == "Open"):
            self.log("Just opened front door")
            self.just_opened_door = True
            self.run_in(self.reset_just_opened, 90)

    def reset_just_opened(self, kwargs):
        self.log("Front door no longer just opened")
        self.just_opened_door = False
    
    def reset_notification(self, kwargs):
        self.log("Reset notification delay")
        self.just_notified = False

    def mailbox_opened(self, entity, attribute, old, new, kwargs):
        self.log("Mailbox opened")
        self.state = self.get_state(self.mail_sensor)
        if (new == "on"):
            if (entity == self.slot_sensor):
                if (self.state == "Mail" or self.state == "Empty"):
                    self.newState = "Mail"
                    self.log("Mail. Old state: {} - New state: {}".format(self.state, self.newState))
                else:
                    self.newState = "Package and mail"
                    self.log("Mail. Old state: {} - New state: {}".format(self.state, self.newState))

                if (self.state != self.newState and self.just_notified is False):
                    if (self.now_is_between(self.stop_quiet, self.start_quiet) and self.isa == "Home"):

                        self.call_service(globals.notify_ios_isa, message = "You've got {}".format(self.newState))
                        self.just_notified = True
                        self.run_in(self.reset_notification, 60)

                self.attributes['icon'] = "mdi:mailbox"
                self.attributes['latest_emptied'] = self.get_state(self.mail_sensor, attribute="latest_emptied")
                self.attributes['latest_mail']=self.local_time_str(datetime.datetime.now(datetime.timezone.utc))
                self.set_state(self.mail_sensor, state=self.newState, attributes=self.attributes)

            elif (entity == self.door_sensor):
                self.package_or_emptied(entity, old, new)


    def package_or_emptied(self, entity, old, new):
        if (entity == self.door_sensor):

            if (self.just_opened_door or self.isa == "Just arrived" or self.stefan == "Just arrived"):
                self.mailbox_emptied()
            else:
                self.new_package()
        
    def mailbox_emptied(self):
        self.call_service(globals.notify_ios_isa, message = "Mailbox emptied")
            
        self.attributes['icon'] = "mdi:dots-horizontal"
        self.attributes['latest_emptied'] = self.local_time_str(datetime.datetime.now(datetime.timezone.utc))
        self.attributes['latest_mail']=self.get_state(self.mail_sensor, attribute="latest_mail")
        self.newState = "Empty"
        self.set_state(self.mail_sensor, state=self.newState, attributes=self.attributes)
        self.log("Mailbox emptied")
    
    def new_package(self):
        if (self.state == "Package" or self.state == "Empty"):
            self.newState = "Package"
            self.log("Package. Old state: {} - New state: {}".format(self.state, self.newState))
        else:
            self.newState = "Package and mail"
            self.log("Package. Old state: {} - New state: {}".format(self.state, self.newState))
            
        if (self.state != self.newState and self.just_notified is False):
            if (self.now_is_between(self.stop_quiet, self.start_quiet) and self.get_state(PEOPLE['Isa']['device_tracker']) == "Home"):

                self.call_service(globals.notify_ios_isa, message = "You've got {}".format(self.newState))
                self.just_notified = True
                self.run_in(self.reset_notification, 60)

        self.attributes['icon'] = "mdi:mailbox"
        # self.attributes['latest_emptied'] = local_time_str(datetime.datetime.now(datetime.timezone.utc))
        self.attributes['latest_emptied'] = self.get_state(self.mail_sensor, attribute="latest_emptied")
        self.attributes['latest_mail']=self.local_time_str(datetime.datetime.now(datetime.timezone.utc))
        self.set_state(self.mail_sensor, state=self.newState, attributes=self.attributes)
        self.log("Check mail")
    
    def make_sensor(self):
        attributes = {}       
        attributes['icon'] = "mdi:dots-horizontal"
        attributes['latest_emptied'] = "Unknown"
        attributes['latest_mail'] = "Unknown"
        self.set_state(self.mail_sensor, state="Empty", attributes=attributes)

    def local_time_str(self, utc_datetime):
        now_timestamp = time.time()
        offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.utcfromtimestamp(now_timestamp)
        local_datetime = utc_datetime + offset
        return local_datetime.strftime("%Y-%m-%d %H:%M")