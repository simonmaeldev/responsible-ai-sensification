import QtQuick
import Score.UI as UI

Rectangle {
  id: root
  width: 320
  height: 200
  color: "black"

  property bool sawLoading: false
  property bool sawRunning: false
  property bool sawDone: false

  function localPath(url) {
    var path = url.toString();
    return path.indexOf("file://") === 0 ? path.slice(7) : path;
  }

  Component.onCompleted: {
    console.log("RAI_SCORE_SMOKE_UI_STARTED");
    createDevice.start();
  }

  Timer {
    id: createDevice
    interval: 1000
    repeat: false
    onTriggered: {
      console.log("RAI_SCORE_SMOKE_CREATE_DEVICE");
      var devicePath = root.localPath(Qt.resolvedUrl("../websocket-device.qml"));
      var deviceCode = Score.readFile(devicePath);
      console.log("RAI_SCORE_SMOKE_DEVICE_CODE " + deviceCode.length);
      if (deviceCode.length === 0) {
        console.error("RAI_SCORE_SMOKE_ERROR could not read " + devicePath);
        return;
      }
      Score.createDevice(
        "RAI Workbench",
        "59e81303-af24-4559-b33d-1c6f59f0f017",
        {
          Address: "ws://127.0.0.1:8080/ws/stream",
          Text: deviceCode,
        }
      );
      console.log("RAI_SCORE_SMOKE_DEVICE_CREATED");
      activateControls.start();
    }
  }

  Timer {
    id: activateControls
    interval: 1500
    repeat: false
    onTriggered: controlsLoader.active = true
  }

  Loader {
    id: controlsLoader
    active: false
    sourceComponent: controlsComponent
  }

  Component {
    id: controlsComponent

    Item {
      id: controls

      property string promptValue: ""
      property int maxTokensValue: 200
      property bool startValue: false
      property bool stopValue: false
      property string runState: ""
      property string runError: ""
      property string loadingLabel: ""
      property real loadingProgress: -1
      property string tokenText: ""
      property string modelName: ""
      property string probeId: ""
      property int featureIndex: -1
      property string featureDescription: ""

      UI.AddressSource on promptValue {
        address: "RAI Workbench:/run/prompt"
        receiveUpdates: false
      }
      UI.AddressSource on maxTokensValue {
        address: "RAI Workbench:/run/max_tokens"
        receiveUpdates: false
      }
      UI.AddressSource on startValue {
        address: "RAI Workbench:/run/start"
        receiveUpdates: false
      }
      UI.AddressSource on stopValue {
        address: "RAI Workbench:/run/stop"
        receiveUpdates: false
      }
      UI.AddressSource on runState {
        address: "RAI Workbench:/run/state"
        sendUpdates: false
      }
      UI.AddressSource on runError {
        address: "RAI Workbench:/run/error"
        sendUpdates: false
      }
      UI.AddressSource on loadingLabel {
        address: "RAI Workbench:/loading/label"
        sendUpdates: false
      }
      UI.AddressSource on loadingProgress {
        address: "RAI Workbench:/loading/progress"
        sendUpdates: false
      }
      UI.AddressSource on tokenText {
        address: "RAI Workbench:/token/text"
        sendUpdates: false
      }
      UI.AddressSource on modelName {
        address: "RAI Workbench:/model/name"
        sendUpdates: false
      }
      UI.AddressSource on probeId {
        address: "RAI Workbench:/probes/1/id"
        sendUpdates: false
      }
      UI.AddressSource on featureIndex {
        address: "RAI Workbench:/features/1/index"
        sendUpdates: false
      }
      UI.AddressSource on featureDescription {
        address: "RAI Workbench:/features/1/description"
        sendUpdates: false
      }

      Timer {
        interval: 300
        running: true
        repeat: false
        onTriggered: {
          controls.promptValue = "Phase 1 score smoke";
          controls.maxTokensValue = 1;
          controls.startValue = !controls.startValue;
        }
      }

      Timer {
        id: sendStop
        interval: 100
        repeat: false
        onTriggered: controls.stopValue = !controls.stopValue
      }

      function reportResult() {
        var result = {
          sawLoading: root.sawLoading,
          sawRunning: root.sawRunning,
          sawDone: root.sawDone,
          runError: controls.runError,
          loadingLabel: controls.loadingLabel,
          loadingProgress: controls.loadingProgress,
          tokenText: controls.tokenText,
          modelName: controls.modelName,
          probeId: controls.probeId,
          featureIndex: controls.featureIndex,
          featureDescription: controls.featureDescription,
        };
        console.log("RAI_SCORE_SMOKE_RESULT " + JSON.stringify(result));
      }

      onRunStateChanged: {
        if (runState === "loading") {
          root.sawLoading = true;
        } else if (runState === "running") {
          root.sawRunning = true;
        } else if (runState === "done") {
          root.sawDone = true;
          sendStop.start();
        } else if (runState === "error") {
          controls.reportResult();
        } else if (runState === "stopped") {
          controls.reportResult();
        }
      }
    }
  }
}
