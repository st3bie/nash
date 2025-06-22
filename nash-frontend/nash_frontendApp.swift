// nashApp.swift - Your main app file (replace existing if you have one)
import SwiftUI

@main
struct nash_frontendApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .background(.clear)
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 800, height: 600)
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Force window transparency
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            if let window = NSApplication.shared.windows.first {
                window.isOpaque = false
                window.backgroundColor = NSColor.clear
                window.hasShadow = true
                window.level = .floating
                window.titlebarAppearsTransparent = true
                window.titleVisibility = .hidden
                window.styleMask.insert(.fullSizeContentView)
                
                // FORCE transparency
                window.contentView?.wantsLayer = true
                window.contentView?.layer?.backgroundColor = NSColor.clear.cgColor
            }
        }
    }
}
