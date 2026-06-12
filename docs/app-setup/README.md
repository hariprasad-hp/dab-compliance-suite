# Application and App Store Setup Guide

## Why app setup is required

Some DAB tests install, launch, and uninstall an application on the DUT. DUT
means Device Under Test. These tests need an application package that can
actually be installed on that device.

## Why the suite does not provide or hardcode a default app

The DAB Compliance Test Suite is generic. It is used across different products,
operating systems, app stores, and package formats. Because of that, the suite
cannot know which app, APK, app store, or store URL is valid for every device.

Users must provide an app that is safe to install and uninstall during testing.
Do not upload random apps. Use a known test app that your DUT can install,
launch, and remove safely.

## Choosing an application for your DUT

Choose an application package based on the DUT platform. The package must match
the install format supported by that platform.

The app should:

- Be supported by the DUT platform.
- Be safe to install and uninstall during repeated test runs.
- Not require user accounts, payments, or manual setup to complete the test.
- Be reachable by the DUT when served by the test tool.

## Android TV / Google TV example

For Android TV and Google TV devices, the application package can be a valid APK
or APKS file.

Run:

```bash
python3 main.py --init
```

When prompted, provide the full path to the APK or APKS file. The tool copies
the configured package under `config/apps/` for later install tests.

## Other platform example

For non-Android platforms, use the package format supported by that platform.
For example, if your platform expects a vendor-specific package type, provide a
valid package in that format during `--init`.

The test suite does not convert packages between platforms. The package you
provide must already be installable by the DUT.

## App store URL setup

Some tests use `applications/install-from-app-store`. For those tests, provide
an app store URL that is valid for the DUT platform and reachable from the DUT.

The app store URL should point to an app supported by that platform and store.
Use `python3 main.py --init` to configure the URL when prompted.

## How the script recognizes the configured app

The setup flow stores the configured application package under `config/apps/`.
Install tests use that configured artifact when `applications/install` is
applicable for the DUT.

Run:

```bash
python3 main.py --init
```

The setup flow collects:

1. Full path to the DUT-compatible application package.
2. App store URL for install-from-app-store tests, if needed.

## Troubleshooting

### App package cannot be installed

Make sure the package format matches the DUT platform. Android TV and Google TV
devices can use APK or APKS packages. Other devices must use the package format
supported by that platform.

### App store install test fails

Make sure the configured app store URL is valid, reachable from the DUT, and
points to an app supported by that platform and store.
