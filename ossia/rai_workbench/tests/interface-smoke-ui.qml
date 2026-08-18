import QtQuick

Rectangle {
  id: root
  width: 1120
  height: 760
  color: "black"

  property bool sawLoading: false
  property bool sawRunning: false
  property bool sawDone: false

  Component.onCompleted: console.log("RAI_SCORE_SMOKE_INTERFACE_STARTED")

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
      interfaceLoader.item.promptValue = "Phase 2 interface smoke";
      interfaceLoader.item.maxTokensValue = 1;
      interfaceLoader.item.startRun();
    }
  }

  Timer {
    id: sendStop
    interval: 100
    repeat: false
    onTriggered: interfaceLoader.item.stopRun()
  }

  Timer {
    id: reportError
    interval: 100
    repeat: false
    onTriggered: root.reportResult()
  }

  Connections {
    target: interfaceLoader.item
    ignoreUnknownSignals: true

    function onRunStateChanged() {
      var state = interfaceLoader.item.runState;
      if (state === "loading") {
        root.sawLoading = true;
      } else if (state === "running") {
        root.sawRunning = true;
      } else if (state === "done") {
        root.sawDone = true;
        sendStop.start();
      } else if (state === "error") {
        reportError.start();
      } else if (state === "stopped") {
        root.reportResult();
      }
    }
  }

  function reportResult() {
    var workbench = interfaceLoader.item;
    var firstFeature = workbench.featureAt(0);
    var secondFeature = workbench.featureAt(1);
    var lastFeature = workbench.featureAt(11);
    var result = {
      sawLoading: root.sawLoading,
      sawRunning: root.sawRunning,
      sawDone: root.sawDone,
      connectionState: workbench.connectionState,
      runState: workbench.runState,
      runError: workbench.runError,
      promptValue: workbench.promptValue,
      maxTokensValue: workbench.maxTokensValue,
      loadingLabel: workbench.loadingLabel,
      loadingProgress: workbench.loadingProgressValue,
      tokenText: workbench.tokenText,
      tokenId: workbench.tokenId,
      featureCount: lastFeature === null ? 0 : 12,
      featureIndex: firstFeature === null ? -1 : firstFeature.featureIndex,
      featureActivation: firstFeature === null ? 0 : firstFeature.featureActivation,
      featureDescription: firstFeature === null ? "" : firstFeature.featureDescription,
      secondFeatureIndex: secondFeature === null ? -1 : secondFeature.featureIndex,
    };
    console.log("RAI_SCORE_SMOKE_RESULT " + JSON.stringify(result));
  }
}
