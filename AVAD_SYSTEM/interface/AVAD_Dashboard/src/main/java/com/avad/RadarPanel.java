package com.avad;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import javax.swing.JPanel;
import org.json.JSONObject;

public class RadarPanel extends JPanel {
    private BufferedImage currentFrame;
    private JSONObject latestTelemetry;
    
    private final Color RADAR_GREEN = new Color(0, 255, 0, 200);
    private final Color RADAR_RED = new Color(255, 0, 0, 200);
    private final Color TEXT_COLOR = new Color(0, 255, 255);

    public RadarPanel() {
        setBackground(Color.BLACK);
    }

    public synchronized void updateFrame(BufferedImage frame) {
        this.currentFrame = frame;
        repaint();
    }

    public synchronized void updateTelemetry(JSONObject telemetry) {
        this.latestTelemetry = telemetry;
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2d = (Graphics2D) g;
        
        // Anti-aliasing
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2d.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        
        int w = getWidth();
        int h = getHeight();

        // 1. Draw Camera Feed
        if (currentFrame != null) {
            g2d.drawImage(currentFrame, 0, 0, w, h, null);
        } else {
            g2d.setColor(RADAR_GREEN);
            g2d.setFont(new Font("Monospaced", Font.BOLD, 24));
            g2d.drawString("NO SIGNAL FROM RELAY...", w/2 - 150, h/2);
        }

        // 2. Draw Target Overlay if Telemetry exists
        if (latestTelemetry != null) {
            boolean detected = latestTelemetry.getBoolean("detected");
            
            if (detected && latestTelemetry.has("box")) {
                JSONObject box = latestTelemetry.getJSONObject("box");
                JSONObject coords = latestTelemetry.getJSONObject("coords");
                double dist = latestTelemetry.getDouble("distance");
                
                // Scale factors mapping OpenCV raw 640x480 to JFrame width/height
                double scaleX = w / 640.0;
                double scaleY = h / 480.0;
                
                int bx = (int) (box.getInt("x") * scaleX);
                int by = (int) (box.getInt("y") * scaleY);
                int bw = (int) (box.getInt("w") * scaleX);
                int bh = (int) (box.getInt("h") * scaleY);
                
                int cx = bx + bw/2;
                int cy = by + bh/2;
                
                // Draw Target Box
                g2d.setColor(RADAR_RED);
                g2d.setStroke(new BasicStroke(3));
                g2d.drawRect(bx, by, bw, bh);
                
                // Draw Crosshair on Target
                g2d.drawLine(cx - 20, cy, cx + 20, cy);
                g2d.drawLine(cx, cy - 20, cx, cy + 20);
                
                // HUD near target
                g2d.setColor(RADAR_GREEN);
                g2d.setFont(new Font("Monospaced", Font.BOLD, 14));
                g2d.drawString("LOCKED: " + dist + "m", bx, by - 5);
                g2d.drawString(String.format("T(X:%.1f, Y:%.1f, Z:%.1f)", 
                        coords.getDouble("x"), coords.getDouble("y"), coords.getDouble("z")), bx, by + bh + 15);
            }
            
            // 3. Draw Global HUD
            g2d.setColor(RADAR_GREEN);
            g2d.setFont(new Font("Monospaced", Font.BOLD, 16));
            
            // Static Crosshair Center
            g2d.setStroke(new BasicStroke(1));
            g2d.drawLine(w/2 - 50, h/2, w/2 + 50, h/2);
            g2d.drawLine(w/2, h/2 - 50, w/2, h/2 + 50);
            
            // Circles
            g2d.drawOval(w/2 - 150, h/2 - 150, 300, 300);
            g2d.drawOval(w/2 - 300, h/2 - 300, 600, 600);
            
            // Left Panel Specs
            int panelX = 20;
            int panelY = 30;
            g2d.drawString("=== AVAD WEAPON SYS ===", panelX, panelY);
            
            JSONObject cam = latestTelemetry.getJSONObject("camera");
            JSONObject laser = latestTelemetry.getJSONObject("laser");
            
            g2d.setColor(TEXT_COLOR);
            g2d.drawString(String.format("CAM PAN:  %.1f°", cam.getDouble("pan")), panelX, panelY + 30);
            g2d.drawString(String.format("CAM TILT: %.1f°", cam.getDouble("tilt")), panelX, panelY + 50);
            
            g2d.setColor(Color.YELLOW);
            g2d.drawString(String.format("LSR PAN:  %.1f°", laser.getDouble("pan")), panelX, panelY + 80);
            g2d.drawString(String.format("LSR TILT: %.1f°", laser.getDouble("tilt")), panelX, panelY + 100);
            
            g2d.setColor(Color.WHITE);
            g2d.drawString(String.format("AI FPS: %.1f", latestTelemetry.getDouble("server_fps")), panelX, h - 30);
            
            if (detected) {
                g2d.setColor(Color.RED);
                g2d.setFont(new Font("Monospaced", Font.BOLD, 22));
                g2d.drawString("WARNING: HOSTILE TRACKED", w/2 - 140, 40);
            } else {
                g2d.setColor(Color.GREEN);
                g2d.setFont(new Font("Monospaced", Font.BOLD, 20));
                g2d.drawString("SCANNING AREA...", w/2 - 90, 40);
            }
        }
    }
}
