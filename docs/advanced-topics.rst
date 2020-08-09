Advanced topics
===============

Sniff device data
-----------------

Meross is continuously releasing new smart devices on the market.
The library has been developed in order to automatically discover and support most of the basic
functions that such devices expose. However, as new devices are released by Meross, also new feature may arise.
In such cases, you may collect low-level data using a specific sniffing tool: `meross_sniffer`.

The sniffing tool basically listens for commands that the Meross App sends to the device and registers its "responses".
In this way, one can use the sniffer tool to collect the data exchanged by the Meross App and the device.

The tool is pretty easy to use: run the program, select the device you want to sniff data from and start to
play with the devide from the Meross App. Once you have tested the feature of interest, wait a bit and then
press ENTER to stop the sniffer. The collected data will be zipped into a folder named data.zip, that you may upload
on github in order to support the feature implementation.

.. warning::
   Even though the sniffing utility has been designed to not gather user's credentials, there is no
   way to make sure the Meross App does not send sensitive information over the network. For this reason,
   you should always change your password before using this utility. It's strongly advised to create an ad-hoc
   account for this matter.

.. note::
   In case you decide to use a dedicated Meross account for the sniffing tool, make sure to remove the device
   you want to sniff from your original account and add it to your new account, which you will use for the sniffing.

In order to use the sniffing tool, perform the following:

- Create a new Meross Account to use for the sniffing tool (alternatively, change the password of your current account)
- Make sure the device you want to sniff data from/to is added to your Meross Account and is ON and ONLINE
- Start the MerossSniffing tool (with the following command)

  .. code-block:: bash

     meross_sniffer

- Log-in with your Meross credentials
- Select the device you want to gather info from and make sure its reported status is ONLINE
- Play with the device using the Meross App: make sure to test all the features of the device if that device is not yet supported by the MerossIot library
- Once done, press ENTER
- Upload the *data.zip* file that was generated in the directory where the utility has been run

