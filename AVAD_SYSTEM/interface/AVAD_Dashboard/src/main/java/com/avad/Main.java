package com.avad;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import javax.swing.JFrame;
import javax.swing.SwingUtilities;

public class Main {
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            createAndShowGUI();
        });
    }

    private static void createAndShowGUI() {
        JFrame frame = new JFrame("AVAD Radar Dashboard");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setLayout(new BorderLayout());
        
        // Frame Size
        frame.setPreferredSize(new Dimension(800, 600));
        frame.getContentPane().setBackground(Color.BLACK);
        
        // Add Radar UI
        RadarPanel radarPanel = new RadarPanel();
        frame.add(radarPanel, BorderLayout.CENTER);
        
        frame.pack();
        frame.setLocationRelativeTo(null);
        frame.setVisible(true);

        // Start Network Engine
        NetworkEngine engine = new NetworkEngine(radarPanel);
        engine.start();

        // Shutdown Hook
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            engine.stop();
        }));
    }
}
