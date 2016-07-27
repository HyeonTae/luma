## Synopsis

Capsule is a program designed to crawl all of the UIs of an Android app and store the view
hierarchies, screenshots, and relationships between views. It attempts to click on all clickable
components and reach as many unique views as possible.

Capsule requires an Android emulator or phone using a debug version of Android and uses the
[AndroidViewClient](https://github.com/dtmilano/AndroidViewClient) library and
[Android Debug Bridge](https://developer.android.com/studio/command-line/adb.html) commands to
communicate with the device.

The application considers views to be distinct if they have a different activity name, fragment
composition, or view hierarchy.

## Code Example

If Capsule is run with no command line arguments with the command, it crawls the current app
(assuming that the current view is the starting view of the app.)


```$ python main.py```

If a text file is passed in as a command line argument, Capsule attempts to crawl each app listed
in the file (one app per line), assuming that all of the packages are already installed on the
device.

```$ python main.py /[PATH TO FILE]/list.txt```


If a directory is passed in as an argument, Capsule installs, crawls, and uninstalls each of the
apps in the directory in alphabetical order.

```$ python main.py /[PATH TO APKS]/```


## Motivation

Capsule serves many purposes, included automated testing and acquiring large samples of Android UIs
with very little effort. Developers can use it to test the behavior of all of their clickable
components and can find bugs, crashes, and possible user traces without having to rely on a testing
framework or change the tests as the app’s UIs change. Although exhaustively searching each app will
not replicate typical user behavior, it can help gain a large corpus of data and find bugs or
unintended app behaviors.

## Installation

To use Capsule, you must have AndroidViewClient installed.

If you are just cloning this repo, you can either directly install AndroidViewClient by reading the
instructions on
[dtmilano’s wiki](https://github.com/dtmilano/AndroidViewClient/wiki#using-easy_install) or by:

``$ sudo apt-get install python-setuptools # not needed on Ubuntu``

``$ sudo easy_install --upgrade androidviewclient``

However, if you have [installed Vanadium](https://vanadium.github.io/installation/), you can import
the luma and luma.third_party repositories by adding the luma manifest to your .jiri_manifest file
or adding it to your manifest from the command line:
``$ jiri import -name=manifest luma https://vanadium.googlesource.com/manifest && jiri update``

After this, you will need to add the AndroidViewClient to your PYTHONPATH:
``export PYTHONPATH=$PYTHONPATH:$JIRI_ROOT/release/projects/luma_third_party/AndroidViewClient/``

## Contributors

We are happy to accept contributions. However, Vanadium does not accept pull requests, so you must
follow the [Vanadium contributing](https://vanadium.github.io/community/contributing.html)
instructions.
In addition, feel free to file issues on the
[luma issue tracker](https://github.com/vanadium/luma/issues) or contact the Capsule engineering
lead, [Dan Afergan](afergan@google.com)

## License
This is not an official Google product.

Capsule is governed by BSD-style license found in the
[luma LICENSE file](https://github.com/vanadium/luma/blob/master/LICENSE).


Capsule lives in the Vanadium codebase, but is no longer affiliated with Vanadium.
