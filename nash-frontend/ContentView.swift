// ContentView.swift - CLI Tool Background
import SwiftUI

struct ContentView: View {
    @State private var mouseLocation = CGPoint(x: 400, y: 300)
    @State private var gradientOffset = CGPoint(x: 0, y: 0)
    @State private var wavePhase: Double = 0
    @State private var persistentMouseWave: Double = 0
    @State private var rippleEffects: [RippleEffect] = []
    @State private var waveEffects: [WaveEffect] = []
    
    let timer = Timer.publish(every: 0.03, on: .main, in: .common).autoconnect() // Slower 30fps for smoother waves
    
    var body: some View {
        ZStack {
            // BLURRED TRANSPARENT BACKGROUND for CLI
            VisualEffectView(material: .hudWindow, blendingMode: .behindWindow)
                .ignoresSafeArea()
            
            // Slow-moving wave gradient that responds to mouse with persistence
            LinearGradient(
                colors: [
                    Color(red: 1.0, green: 0.612, blue: 0.992).opacity(0.25), // FF9CFD
                    Color(red: 0.686, green: 0.933, blue: 1.0).opacity(0.25)  // AFEEFF
                ],
                startPoint: UnitPoint(
                    x: 1.0 + gradientOffset.x * 0.0003 + sin(wavePhase + persistentMouseWave) * 0.08,
                    y: 0.0 + gradientOffset.y * 0.0003 + cos(wavePhase * 0.7 + persistentMouseWave) * 0.06
                ),
                endPoint: UnitPoint(
                    x: 0.0 - gradientOffset.x * 0.0003 + cos(wavePhase * 0.5 + persistentMouseWave) * 0.07,
                    y: 1.0 - gradientOffset.y * 0.0003 + sin(wavePhase * 0.8 + persistentMouseWave) * 0.05
                )
            )
            .ignoresSafeArea()
            .animation(.easeOut(duration: 0.8), value: gradientOffset) // Slower, smoother animation
            
            // Ripple effects (kept for interaction feedback)
            ForEach(rippleEffects.indices, id: \.self) { index in
                let ripple = rippleEffects[index]
                Circle()
                    .stroke(Color.white.opacity(0.3), lineWidth: 1)
                    .frame(width: ripple.size, height: ripple.size)
                    .position(ripple.position)
                    .opacity(ripple.opacity)
                    .scaleEffect(ripple.scale)
            }
            
            // Wave effects (kept for interaction feedback)
            ForEach(waveEffects.indices, id: \.self) { index in
                let wave = waveEffects[index]
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [
                                Color.white.opacity(wave.opacity * 0.2),
                                Color.white.opacity(wave.opacity * 0.05),
                                Color.clear
                            ],
                            center: .center,
                            startRadius: 0,
                            endRadius: wave.radius
                        )
                    )
                    .frame(width: wave.radius * 2, height: wave.radius * 2)
                    .position(wave.position)
            }
            
            // PLACEHOLDER FOR TERMINAL CONTENT - Python script will handle this
            /*
            // Terminal simulation will go here
            // Python script will send commands to display terminal content
            // VStack {
            //     // Terminal header, prompt, output, etc.
            // }
            */
        }
        .onReceive(timer) { _ in
            wavePhase += 0.02 // Much slower wave motion
            updateEffects()
        }
        .onContinuousHover { phase in
            switch phase {
            case .active(let location):
                mouseLocation = location
                let centerX = 400.0
                let centerY = 300.0
                
                // Update gradient with persistent wave influence
                gradientOffset = CGPoint(
                    x: (location.x - centerX) + sin(wavePhase * 1.2) * 30,
                    y: (location.y - centerY) + cos(wavePhase * 0.9) * 20
                )
                
                // Add persistent mouse wave that continues after mouse stops
                persistentMouseWave += 0.05
                
            case .ended:
                // Continue wave motion but gradually return to center
                gradientOffset = CGPoint(
                    x: sin(wavePhase * 0.8) * 15,
                    y: cos(wavePhase * 0.6) * 10
                )
                // persistentMouseWave continues - this gives the persistent effect
            }
        }
        .onTapGesture { location in
            // Subtle interaction for CLI feel
            createRipple(at: location)
        }
    }
    
    func createRipple(at position: CGPoint) {
        let ripple = RippleEffect(position: position)
        rippleEffects.append(ripple)
        
        withAnimation(.easeOut(duration: 1.5)) { // Slower ripples
            if let index = rippleEffects.firstIndex(where: { $0.id == ripple.id }) {
                rippleEffects[index].scale = 2.0 // Smaller ripples
                rippleEffects[index].opacity = 0.0
                rippleEffects[index].size = 150
            }
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            rippleEffects.removeAll { $0.id == ripple.id }
        }
    }
    
    func createWave(at position: CGPoint) {
        let wave = WaveEffect(position: position)
        waveEffects.append(wave)
        
        withAnimation(.easeOut(duration: 3.0)) { // Much slower waves
            if let index = waveEffects.firstIndex(where: { $0.id == wave.id }) {
                waveEffects[index].radius = 250
                waveEffects[index].opacity = 0.0
            }
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
            waveEffects.removeAll { $0.id == wave.id }
        }
    }
    
    func updateEffects() {
        // Update ripple effects
        for i in rippleEffects.indices {
            rippleEffects[i].size += 1
            rippleEffects[i].opacity *= 0.99
        }
        
        // Update wave effects
        for i in waveEffects.indices {
            waveEffects[i].radius += 0.8
            waveEffects[i].opacity *= 0.998
        }
        
        // Remove finished effects
        rippleEffects.removeAll { $0.opacity < 0.01 }
        waveEffects.removeAll { $0.opacity < 0.01 }
    }
}

// Visual Effect View for CLI background blur
struct VisualEffectView: NSViewRepresentable {
    let material: NSVisualEffectView.Material
    let blendingMode: NSVisualEffectView.BlendingMode
    
    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = material
        view.blendingMode = blendingMode
        view.state = .active
        view.wantsLayer = true
        return view
    }
    
    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
        nsView.material = material
        nsView.blendingMode = blendingMode
    }
}

struct RippleEffect: Identifiable {
    let id = UUID()
    let position: CGPoint
    var size: CGFloat = 20
    var opacity: Double = 1.0
    var scale: CGFloat = 1.0
}

struct WaveEffect: Identifiable {
    let id = UUID()
    let position: CGPoint
    var radius: CGFloat = 50
    var opacity: Double = 1.0
}

#Preview {
    ContentView()
}
