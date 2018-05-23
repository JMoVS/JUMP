# Getting started with JUMP

## System requirements
- NI-VISA driver software (check [NI-VISA](http://search.ni.com/nisearch/app/main/p/ap/tech/lang/en/pg/1/sn/ssnav:ndr/aq/AND(nicontenttype:driver,%20sitesection:ndr,%20AND%20(OR(nigen10:1640,%20productcategories:1640,%20%22NI-VISA%22)%20,%20OR(nilanguage:en,%20nilanguage:en)))/) )
- an operating system that is compatible with NI-VISA (Windows 7 or newer, Scientific Liunux, MacOS)
- Python 3 with the [pyVISA package](https://pyvisa.readthedocs.io/en/stable/#) (This guide is with Anaconda (Python 3.x version), available at [Continuum](https://www.anaconda.com/download/) free of charge)
- A Python IDE, I recommend [Pycharm Community Edition](https://www.jetbrains.com/pycharm/download)
- [Optional:] If you want to receive updates easier, and push improvements back to the project for everybody, you'll also need to get [https://git-scm.com/](https://git-scm.com/) installed and/or consider a free github account and their [Github Desktop app](https://desktop.github.com/). In any case, I'd be happy to help you get going so feel free to reach out to me at jump@justinscholz.de

## Installing

1. Start with a working operating system, make sure your system is up to date and that windows can't auto-reboot when it thinks it should (funnily enough this is how a lot of measurements fail in the beginning).

2. Install NI-VISA in the latest available version. Leave all boxes checked and make sure to install NI-MAX with it (makes debugging and identifying programs easier).

3. Install Python 3 with Anaconda. So install Anaconda, follow the installer. We need a python enviornment with PyVISA installed. So make sure ```conda``` is installed, and make yourself acquainted with the [Getting started with Conda](https://conda.io/docs/user-guide/getting-started.html) guide. No worries, I'll give you detailed instrcutions.

4. Follow the steps in the conda getting started guide and [start Conda](https://conda.io/docs/user-guide/getting-started.html#starting-conda), follow the guide and create an environment (the name is not important, but you should remember it. I suggest *JUMP* as the name for the environment). Install pip:
```
conda install -n JUMP pip
```

Activate the environment.

5. Update pip and install PyVISA in the environment:
```
pip install --upgrade pip # *Follow the instructions, confirm updates*
pip install PyVISA
```

6. Install PyCharm Community Edition.

7. Download a copy of JUMP (https://github.com/JMoVS/JUMP/releases) and unpack it to a folder of your choice, probably somewhere in your users directory. Open the containing folder (eg ```JUMP-0.3.0```). 

8. In PyCharm, click on "Run"->"Edit Configurations" and add a new "Python" configuration with the "+" symbol. Give it a name (eg ```JUMP```) and as script path, select the "MeasurementProgram.py" python script in the JUMP folder. As python interpreter, go to (on Windows) C:\Users\$USERNAME$\Anaconda3\envs and choose the "python.exe" that is linked there. 

9. Now if you select the "JUMP" run configuration, you should be able to get the program running and see it in the interactive prompt in the bottom half of your PyCharm window. 

10. Now follow the guide to get device serials and integrate them into your setup so that you can start measuring.