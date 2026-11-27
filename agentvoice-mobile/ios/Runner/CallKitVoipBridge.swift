import AVFoundation
import CallKit
import Foundation

/// CallKit bridge strictly for AgentVoice VoIP calls (never normal cellular calls).
final class CallKitVoipBridge: NSObject, CXProviderDelegate {
    private let provider: CXProvider
    private let callController = CXCallController()

    override init() {
        let config = CXProviderConfiguration()
        config.supportsVideo = false
        config.maximumCallsPerCallGroup = 1
        config.supportedHandleTypes = [.generic, .phoneNumber]
        self.provider = CXProvider(configuration: config)
        super.init()
        self.provider.setDelegate(self, queue: nil)
    }

    func startVoipCall(uuid: UUID, handle: String) {
        let cxHandle = CXHandle(type: .generic, value: handle)
        let startAction = CXStartCallAction(call: uuid, handle: cxHandle)
        let tx = CXTransaction(action: startAction)
        callController.request(tx) { _ in }
    }

    func providerDidReset(_ provider: CXProvider) {}

    func provider(_ provider: CXProvider, perform action: CXStartCallAction) {
        configureAudioSession()
        action.fulfill()
    }

    func provider(_ provider: CXProvider, perform action: CXEndCallAction) {
        try? AVAudioSession.sharedInstance().setActive(false)
        action.fulfill()
    }

    private func configureAudioSession() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth])
        try? session.setActive(true)
    }
}
