// Prints a wall-clock timestamp for every space key press (listen-only, records nothing else).
import CoreGraphics
import Foundation

setvbuf(stdout, nil, _IOLBF, 0)
let mask = CGEventMask(1 << CGEventType.keyDown.rawValue)
guard let tap = CGEvent.tapCreate(
    tap: .cgSessionEventTap, place: .headInsertEventTap, options: .listenOnly,
    eventsOfInterest: mask,
    callback: { _, _, event, _ in
        if event.getIntegerValueField(.keyboardEventKeycode) == 49,
           event.getIntegerValueField(.keyboardEventAutorepeat) == 0 {
            print(String(format: "%.3f SPACE", Date().timeIntervalSince1970))
        }
        return Unmanaged.passUnretained(event)
    }, userInfo: nil)
else {
    print("NO_PERMISSION: allow Input Monitoring for your terminal app")
    exit(1)
}
CFRunLoopAddSource(CFRunLoopGetCurrent(), CFMachPortCreateRunLoopSource(nil, tap, 0), .commonModes)
CFRunLoopRun()
