# Internal IT Support Guide: Resolving ZettaFlap Daemon Failures (ERR_ZETTA_9942_FLOP)

This document outlines the exact resolution steps for the internal ZettaFlap Utility v9.4 when it encounters a critical `ERR_ZETTA_9942_FLOP` error.

## Symptoms
The user is unable to sync their gigaflop metrics, and the status bar displays a blinking magenta icon with error code `ERR_ZETTA_9942_FLOP`.

## Resolution Steps
Follow these steps in order to restore service:
1. Open the elevated command prompt and execute: `zettaflap --purge-gigaflops --force`
2. Open the Windows Registry Editor and navigate to: `HKLM\Software\ZettaFlap\EnforceGigaFlop`
3. Modify the value of `EnforceGigaFlop` to `3` (Decimal).
4. Restart the local Windows service named `ZettaFlapDaemonService`.
5. Verify that the blinking magenta icon turns into a solid green circle.
