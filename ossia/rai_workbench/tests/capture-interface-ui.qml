import QtQuick
import Score.UI as UI

Rectangle {
  id: root
  width: 1440
  height: 900
  color: "black"

  property string capturePath: "__RAI_CAPTURE_PATH__"
  property bool captureFinished: false
  property bool captureSaved: false
  property bool resultReported: false
  property real exampleMappedValue: -1.0

  UI.PortSource on exampleMappedValue {
    process: "EXAMPLE_patchable_tensor_rms_delete_safe"
    port: 0
  }

  Loader {
    id: interfaceLoader
    anchors.fill: parent
    source: "../interface.qml"
    onLoaded: activateControls.start()
  }

  Timer {
    id: activateControls
    interval: 500
    repeat: false
    onTriggered: {
      interfaceLoader.item.promptValue = "Phase 3 research smoke";
      interfaceLoader.item.maxTokensValue = 2;
      interfaceLoader.item.startRun();
    }
  }

  Timer {
    id: captureDelay
    interval: 300
    repeat: false
    onTriggered: root.captureInterface()
  }

  Connections {
    target: interfaceLoader.item
    ignoreUnknownSignals: true

    function onSnapshotCaptured(count) {
      if (count === 1) {
        interfaceLoader.item.setObservationLayer(7);
        interfaceLoader.item.setProbeLayer(0, 7);
      }
    }

    function onRunStateChanged() {
      var state = interfaceLoader.item.runState;
      if (state === "done") {
        captureDelay.start();
      } else if (state === "stopped" && root.captureFinished) {
        root.reportResult();
      }
    }
  }

  function captureInterface() {
    root.grabToImage(function(result) {
      root.captureSaved = result.saveToFile(root.capturePath);
      root.captureFinished = true;
      interfaceLoader.item.stopRun();
    });
  }

  function reportResult() {
    if (root.resultReported) {
      return;
    }
    root.resultReported = true;
    var workbench = interfaceLoader.item;
    var snapshot = workbench.historyAt(1);
    console.log("RAI_SCORE_SMOKE_RESULT " + JSON.stringify({
      saved: root.captureSaved,
      capturePath: root.capturePath,
      historyCount: workbench.tokenHistory.length,
      tokenText: snapshot === null ? "" : snapshot.tokenText,
      observationLayer: snapshot === null ? -1 : snapshot.observationLayer,
      backendScalar: snapshot === null ? -1 : snapshot.patchableScalars[0].value,
      exampleMappedValue: root.exampleMappedValue
    }));
  }
}
