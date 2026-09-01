import QtQuick

Rectangle {
  id: root
  width: 640
  height: 360
  color: "black"

  property string deviceName: "RAI Emitter Smoke"
  property int attempts: 0

  Component.onCompleted: {
    Score.connectOSCQueryDevice(root.deviceName, "__RAI_OSCQUERY_URL__");
    poll.start();
  }

  Timer {
    id: poll
    interval: 100
    repeat: true
    onTriggered: {
      root.attempts += 1;
      var rms = Number(Device.read("RAI Emitter Smoke:/rai/probes/1/rms"));
      if (rms === 10.5 || root.attempts >= 150) {
        poll.stop();
        console.log("RAI_SCORE_SMOKE_RESULT " + JSON.stringify({
          connected: rms === 10.5,
          rms: rms,
          model: String(Device.read("RAI Emitter Smoke:/rai/model/name") || ""),
          tokenIndex: Number(Device.read("RAI Emitter Smoke:/rai/run/token/index")),
          tokenText: String(Device.read("RAI Emitter Smoke:/rai/run/token/text") || ""),
          enabled: Boolean(Device.read("RAI Emitter Smoke:/rai/probes/1/enabled")),
          site: String(Device.read("RAI Emitter Smoke:/rai/probes/1/site") || ""),
          layer: Number(Device.read("RAI Emitter Smoke:/rai/probes/1/layer")),
          modulePath: String(Device.read("RAI Emitter Smoke:/rai/probes/1/module_path") || ""),
          shape: String(Device.read("RAI Emitter Smoke:/rai/probes/1/shape") || ""),
          sequence: Number(Device.read("RAI Emitter Smoke:/rai/probes/1/sequence"))
        }));
      }
    }
  }
}
