# Control Program for Lakeshore 475 DSP Gaussmeter
import visa


class GaussMeter():

    def __init__(self, address):
        self.rm = visa.ResourceManager()
        # Depending on instrument GPIB address
        # 475 Gaussmeter GPIB address 7?
        self.gm = self.rm.open_resource(address)
        # self.gm.write("")
        # self.gm = self.gm.write("QTST?")
        print("Gaussmeter Initialized")

    def test_mode(self):
        print(self.gm.query("RDGMODE?"))

    # def set_mode(self):
        # self.gm.write("1,3,1,1,1") # sets to DC measurement with 5 digits accuracy
        # self.gm.write("UNIT 3") # sets the units to Oe

    def measure(self):
        # print(self.gm.query("RDGFIELD?"))
        return float(self.gm.query("RDGFIELD?"))

    # properly closes the open resource, if not done then rm.close() will throw an visaIOerror
    def shutdown(self):
        del self.gm


if __name__ == '__main__':
    rm = visa.ResourceManager()
    print(rm.list_resources())
    rm.close()
