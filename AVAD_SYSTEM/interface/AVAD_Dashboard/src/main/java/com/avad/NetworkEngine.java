package com.avad;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.URL;
import java.net.URLConnection;
import javax.imageio.ImageIO;
import org.json.JSONObject;

public class NetworkEngine {
    private final RadarPanel panel;
    private final String streamUrl = "http://127.0.0.1:5000/stream";
    private final int udpPort = 12346;
    private boolean isRunning = true;

    public NetworkEngine(RadarPanel panel) {
        this.panel = panel;
    }

    public void start() {
        startTelemetryThread();
        startVideoStreamThread();
    }

    private void startTelemetryThread() {
        new Thread(() -> {
            try (DatagramSocket socket = new DatagramSocket(udpPort)) {
                byte[] buffer = new byte[2048];
                while (isRunning) {
                    DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                    socket.receive(packet);
                    String jsonStr = new String(packet.getData(), 0, packet.getLength(), "UTF-8");
                    JSONObject telemetry = new JSONObject(jsonStr);
                    panel.updateTelemetry(telemetry);
                }
            } catch (Exception e) {
                System.out.println("UDP Telemetry error: " + e.getMessage());
            }
        }).start();
    }

    private void startVideoStreamThread() {
        new Thread(() -> {
            try {
                URL url = new URL(streamUrl);
                while (isRunning) {
                    try {
                        URLConnection conn = url.openConnection();
                        conn.setReadTimeout(5000);
                        InputStream is = conn.getInputStream();
                        // MJPEG simplest parsing (Look for FFD8 and FFD9 keys)
                        byte[] buffer = new byte[1024 * 512]; // 512 KB buffer
                        int bytesRead;
                        int offset = 0;
                        boolean inJpeg = false;
                        int startIdx = -1;
                        
                        while ((bytesRead = is.read(buffer, offset, buffer.length - offset)) != -1 && isRunning) {
                            offset += bytesRead;
                            
                            // find JPEG Start 0xFFD8 and End 0xFFD9
                            for (int i = 0; i < offset - 1; i++) {
                                if ((buffer[i] & 0xFF) == 0xFF && (buffer[i + 1] & 0xFF) == 0xD8) {
                                    startIdx = i;
                                }
                                if ((buffer[i] & 0xFF) == 0xFF && (buffer[i + 1] & 0xFF) == 0xD9 && startIdx != -1) {
                                    int len = (i + 2) - startIdx;
                                    byte[] jpegData = new byte[len];
                                    System.arraycopy(buffer, startIdx, jpegData, 0, len);
                                    
                                    // Decode and send to panel
                                    ByteArrayInputStream bais = new ByteArrayInputStream(jpegData);
                                    BufferedImage img = ImageIO.read(bais);
                                    if(img != null) {
                                        panel.updateFrame(img);
                                    }
                                    
                                    // Shift buffer
                                    int remaining = offset - (i + 2);
                                    System.arraycopy(buffer, i + 2, buffer, 0, remaining);
                                    offset = remaining;
                                    startIdx = -1;
                                    break;
                                }
                            }
                            if (offset >= buffer.length) offset = 0; // Prevent overflow
                        }
                    } catch (Exception ex) {
                        System.out.println("Stream dropped, retrying... " + ex.getMessage());
                        Thread.sleep(1000);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    public void stop() {
        isRunning = false;
    }
}
