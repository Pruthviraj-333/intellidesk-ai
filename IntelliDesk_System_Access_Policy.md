# IntelliDesk System Access & Hardware Troubleshooting Guide

This document outlines the corporate IT policies for accessing internal services remotely via VPN, and resolving common docking station/monitor configuration issues.

---

## SECTION 1: GLOBAL VPN ACCESS & MULTI-FACTOR AUTHENTICATION (MFA)

All employees and contractors accessing the corporate network from outside the physical office must use the **IntelliDesk Global VPN Gateway** (`vpn.intellidesk.ai`).

### VPN Connection Requirements
1. **Authorized Device:** You must connect using your company-issued laptop. Personal devices are strictly prohibited from establishing VPN tunnels.
2. **MFA Requirement:** Connection requires dual authentication. After entering your network username and password, you must approve the push notification on your registered Google Authenticator or Microsoft Authenticator app within 60 seconds.

### Troubleshooting Security Alert 403 (VPN-MFA-ERR-403)
If you receive the error **"VPN access blocked with Security Alert 403 (Code: VPN-MFA-ERR-403)"**, this indicates the gateway blocked your connection. Follow these resolution steps:
*   **Location Mismatch:** Ensure you are not running a personal proxy or geolocation spoofing tool. Connections originating from blacklisted geographical blocks will trigger an automatic 403 lockout.
*   **Authenticator App Time Drift:** If your MFA push or token is rejected repeatedly, open your authenticator app, go to Settings -> Time correction for codes -> Sync now.
*   **Outdated Client Version:** Verify that your FortiClient or OpenVPN version is at least v7.2.1. Older client versions will fail the security posture assessment and result in a 403 error.
*   **IP Lockout Reset:** If locked out, wait 15 minutes for the automated IP restriction to expire before attempting another login.

---

## SECTION 2: DOCKING STATION & MULTI-MONITOR DISPLAY ISSUES

The standard desktop configuration utilizes the **Lenovo ThinkPad Hybrid USB-C with USB-A Dock** connected to dual 27-inch Dell Monitors.

### Resolving Monitor Flickering and Display Dropouts
If one or both of your external displays frequently flicker, turn black, or lose signal:
1. **Firmware Update:** The most common cause is outdated dock firmware. Download and install the **Lenovo Hybrid Dock Firmware Utility v1.10.15** or higher from the IT Service Portal. Restart your computer after the update finishes.
2. **Disable Hardware Acceleration:** Flickering on Electron-based apps (like Slack, Microsoft Teams, or VS Code) or Google Chrome can be fixed by going to the app's settings and unchecking "Use hardware acceleration when available".
3. **Cable Check:** Ensure you are using High-Speed DisplayPort-to-DisplayPort or HDMI-to-HDMI cables. Avoid using passive DP-to-HDMI converters.

### Resolving Dock Charging & USB Device Recognition Issues
If your laptop is not charging while plugged into the USB-C cable from the dock, or external USB keyboard/mouse devices are unrecognized:
*   **Hard Reset the Dock:**
    1. Disconnect the USB-C cable from your laptop.
    2. Unplug the yellow slim-tip power adapter cable from the back of the docking station.
    3. Wait 15 seconds to allow the internal capacitors to fully discharge.
    4. Reconnect the power adapter to the dock, then plug the USB-C cable back into your laptop.
*   **Thunderbolt Driver Reinstallation:** Open Device Manager -> System Devices -> Right-click Intel Thunderbolt Controller -> Click Uninstall. Restart the PC to let Windows reinstall the correct controller driver.
