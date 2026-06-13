# Streaming Setup Guide: GeForce Now via Sunshine & Moonlight

This guide provides instructions for configuring low-overhead game streaming on a Raspberry Pi 3B client using a local powerful PC as the host (Milhy-PC) running Sunshine and GeForce Now.

## Architecture Overview

```
                                  [ Local Network (LAN / Tailscale) ]
+----------------------------+                                         +--------------------------+
|       Milhy-PC (Host)      | -------- Low-Latency Video Stream -----> |  Raspberry Pi 3B (Client)|
|   (Runs GeForce Now &      | <-------- Gamepad / Keyboard Inputs ---- |  (Runs Moonlight Client  |
|    Sunshine Server)        |                                         |   with HW Decoders)      |
+----------------------------+                                         +--------------------------+
  - GTX 1060 or Intel iGPU                                               - Native H.264 HW decode
  - Real-time video encoding                                             - Sub-10ms decoding delay
```

## Step 1: Install and Configure Sunshine on Milhy-PC (Host)

Your host PC runs **MX Linux 25 KDE** with a dual GPU setup (Intel HD Graphics 4600 iGPU + NVIDIA GTX 1060 dGPU).

1. Copy and execute the host installation script on **Milhy-PC**:
   ```bash
   bash install-sunshine-mx.sh
   ```
2. Open the web interface at `https://localhost:47990` and create your credentials.
3. Configure the GPU Encoder strategy in `~/.config/sunshine/sunshine.conf`:
   * **To save NVIDIA resources for AI / LLM workloads:** Use Intel VA-API encoding:
     ```text
     encoder = vaapi
     adapter_name = /dev/dri/renderD128
     ```
   * **For maximum gaming performance:** Use NVIDIA NVENC encoding:
     ```text
     encoder = nvenc
     ```
4. Under the **Applications** tab in the Web UI, add a new application entry for **GeForce Now**:
   * **Application Name:** GeForce Now
   * **Command:** `chromium --kiosk --autoplay-policy=no-user-gesture-required https://play.geforcenow.com`
   * *(Optional)* **Working Directory:** `/home/milhy777`

## Step 2: Install and Configure Moonlight on Raspberry Pi 3B (Client)

1. Copy and execute the client installation script on the **Raspberry Pi**:
   ```bash
   bash install-moonlight.sh
   ```
2. **Reboot the Raspberry Pi** to apply the new group permissions (`input`, `video`, `render`, `tty`):
   ```bash
   sudo reboot
   ```

## Step 3: Pairing Sunshine and Moonlight

1. Start Moonlight on the Raspberry Pi:
   ```bash
   moonlight-qt
   ```
2. Moonlight will automatically scan the local network and locate **Milhy-PC** (or you can manually add its Tailscale IP `100.88.85.89` / LAN IP `192.168.0.205`).
3. Click on the host icon. A **4-digit PIN** will be displayed on the TV screen.
4. On your phone, tablet, or host PC, open the Sunshine Web UI (`https://192.168.0.205:47990` or `https://localhost:47990`).
5. Go to the **PIN** tab, enter the 4-digit PIN displayed on the TV, and click **Send**.
6. The pairing is complete! You can now select "GeForce Now" or any other app to stream.
