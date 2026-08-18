import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Score.UI as UI

Rectangle {
  id: root
  width: 1120
  height: 760
  color: "#101319"

  property alias promptValue: promptInput.text
  property alias maxTokensValue: maxTokensInput.value
  property bool startValue: false
  property bool stopValue: false
  property string connectionState: "disconnected"
  property string runState: "idle"
  property string runError: ""
  property string loadingLabel: ""
  property string loadingDetail: ""
  property real loadingProgressValue: 0.0
  property int tokenId: -1
  property string tokenText: ""
  readonly property bool runBusy: runState === "loading" || runState === "running"

  function startRun() {
    startValue = !startValue;
  }

  function stopRun() {
    stopValue = !stopValue;
  }

  function featureAt(index) {
    return featureRepeater.itemAt(index);
  }

  function connectionColor() {
    if (connectionState === "ready") {
      return "#4dd7a5";
    }
    if (connectionState === "connected") {
      return "#e8bf66";
    }
    return "#ef7182";
  }

  UI.AddressSource on startValue {
    address: "RAI Workbench:/run/start"
    receiveUpdates: false
  }
  UI.AddressSource on stopValue {
    address: "RAI Workbench:/run/stop"
    receiveUpdates: false
  }
  UI.AddressSource on connectionState {
    address: "RAI Workbench:/connection/state"
    sendUpdates: false
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
  UI.AddressSource on loadingDetail {
    address: "RAI Workbench:/loading/detail"
    sendUpdates: false
  }
  UI.AddressSource on loadingProgressValue {
    address: "RAI Workbench:/loading/progress"
    sendUpdates: false
  }
  UI.AddressSource on tokenId {
    address: "RAI Workbench:/token/id"
    sendUpdates: false
  }
  UI.AddressSource on tokenText {
    address: "RAI Workbench:/token/text"
    sendUpdates: false
  }

  ColumnLayout {
    anchors.fill: parent
    anchors.margins: 28
    spacing: 18

    RowLayout {
      Layout.fillWidth: true
      spacing: 12

      ColumnLayout {
        Layout.fillWidth: true
        spacing: 2

        Label {
          text: "RAI WORKBENCH"
          color: "#9ca9bd"
          font.pixelSize: 12
          font.bold: true
          font.letterSpacing: 2
        }
        Label {
          text: "Gemma · SAE · Neuronpedia"
          color: "#f2f5fa"
          font.pixelSize: 26
          font.bold: true
        }
      }

      Rectangle {
        width: connectionLabel.implicitWidth + 30
        height: 34
        radius: 17
        color: "#1a202a"
        border.color: root.connectionColor()

        Row {
          anchors.centerIn: parent
          spacing: 8

          Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 8
            height: 8
            radius: 4
            color: root.connectionColor()
          }
          Label {
            id: connectionLabel
            objectName: "connectionState"
            text: root.connectionState
            color: "#e6ebf3"
            font.pixelSize: 13
          }
        }
      }
    }

    Frame {
      Layout.fillWidth: true
      padding: 18
      background: Rectangle {
        radius: 10
        color: "#171c24"
        border.color: "#2a3341"
      }

      ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
          text: "Prompt"
          color: "#c9d2df"
          font.pixelSize: 13
          font.bold: true
        }

        TextArea {
          id: promptInput
          objectName: "promptInput"
          Layout.fillWidth: true
          Layout.preferredHeight: 84
          placeholderText: "Enter a prompt to inspect…"
          wrapMode: TextEdit.Wrap
          color: "#f2f5fa"
          placeholderTextColor: "#758196"
          font.pixelSize: 16
          selectByMouse: true
          background: Rectangle {
            radius: 7
            color: "#0f1319"
            border.color: promptInput.activeFocus ? "#6ea8fe" : "#323c4b"
          }

          UI.AddressSource on text {
            address: "RAI Workbench:/run/prompt"
          }
        }

        RowLayout {
          Layout.fillWidth: true
          spacing: 10

          Label {
            text: "Maximum tokens"
            color: "#9ca9bd"
            font.pixelSize: 13
          }
          SpinBox {
            id: maxTokensInput
            objectName: "maxTokensInput"
            from: 1
            to: 4096
            value: 200
            editable: true

            UI.AddressSource on value {
              address: "RAI Workbench:/run/max_tokens"
            }
          }
          Item { Layout.fillWidth: true }
          Button {
            id: stopButton
            objectName: "stopButton"
            text: "Stop"
            enabled: root.runBusy
            onClicked: root.stopRun()
          }
          Button {
            id: runButton
            objectName: "runButton"
            text: root.runBusy ? "Running…" : "Run prompt"
            enabled: !root.runBusy && root.connectionState !== "disconnected"
            onClicked: root.startRun()
          }
        }
      }
    }

    Rectangle {
      Layout.fillWidth: true
      Layout.preferredHeight: statusColumn.implicitHeight + 28
      radius: 10
      color: "#171c24"
      border.color: root.runState === "error" ? "#7d3340" : "#2a3341"

      ColumnLayout {
        id: statusColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.margins: 16
        spacing: 8

        RowLayout {
          Layout.fillWidth: true

          Label {
            text: "Run state"
            color: "#9ca9bd"
            font.pixelSize: 12
            font.bold: true
          }
          Label {
            text: root.runState
            color: "#f2f5fa"
            font.pixelSize: 14
          }
          Item { Layout.fillWidth: true }
          Label {
            text: root.loadingLabel
            visible: root.runState === "loading"
            color: "#c9d2df"
            font.pixelSize: 13
          }
        }

        ProgressBar {
          objectName: "loadingProgress"
          Layout.fillWidth: true
          from: 0
          to: 1
          value: root.loadingProgressValue
          visible: root.runState === "loading"
        }
        Label {
          text: root.loadingDetail
          visible: root.runState === "loading" && root.loadingDetail.length > 0
          color: "#8e9aab"
          font.pixelSize: 12
          wrapMode: Text.Wrap
          Layout.fillWidth: true
        }
        Label {
          objectName: "runError"
          text: root.runError
          visible: root.runError.length > 0
          color: "#ff91a0"
          font.pixelSize: 13
          wrapMode: Text.Wrap
          Layout.fillWidth: true
        }
      }
    }

    RowLayout {
      Layout.fillWidth: true
      Layout.fillHeight: true
      spacing: 18

      Rectangle {
        Layout.preferredWidth: 330
        Layout.fillHeight: true
        radius: 10
        color: "#171c24"
        border.color: "#2a3341"

        ColumnLayout {
          anchors.fill: parent
          anchors.margins: 20
          spacing: 12

          Label {
            text: "EXACT CURRENT TOKEN"
            color: "#9ca9bd"
            font.pixelSize: 11
            font.bold: true
            font.letterSpacing: 1.5
          }
          Label {
            objectName: "currentToken"
            Layout.fillWidth: true
            text: JSON.stringify(root.tokenText)
            color: "#f4d58d"
            font.pixelSize: 30
            wrapMode: Text.WrapAnywhere
          }
          Label {
            objectName: "currentTokenId"
            text: root.tokenId >= 0 ? "Token ID  " + root.tokenId : "Token ID  —"
            color: "#aab5c5"
            font.pixelSize: 14
          }
          Item { Layout.fillHeight: true }
          Label {
            Layout.fillWidth: true
            text: "Quoted text preserves whitespace and control characters."
            color: "#758196"
            font.pixelSize: 12
            wrapMode: Text.Wrap
          }
        }
      }

      Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        radius: 10
        color: "#171c24"
        border.color: "#2a3341"

        ColumnLayout {
          anchors.fill: parent
          anchors.margins: 16
          spacing: 10

          RowLayout {
            Layout.fillWidth: true
            Label {
              text: "Strongest active SAE features"
              color: "#f2f5fa"
              font.pixelSize: 18
              font.bold: true
            }
            Item { Layout.fillWidth: true }
            Label {
              text: "RAW ACTIVATION · NEURONPEDIA EVIDENCE"
              color: "#7f8ca0"
              font.pixelSize: 10
              font.bold: true
            }
          }

          ScrollView {
            objectName: "featureList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Column {
              width: parent.width
              spacing: 6

              Repeater {
                id: featureRepeater
                model: 12

                delegate: Rectangle {
                  id: featureRow
                  objectName: "featureRow" + (index + 1)
                  width: featureRepeater.parent.width
                  height: 52
                  radius: 6
                  color: index % 2 === 0 ? "#12171e" : "#151b23"
                  opacity: featureIndex >= 0 ? 1.0 : 0.48

                  property int featureIndex: -1
                  property real featureActivation: 0.0
                  property string featureDescription: ""

                  UI.AddressSource on featureIndex {
                    address: "RAI Workbench:/features/" + (index + 1) + "/index"
                    sendUpdates: false
                  }
                  UI.AddressSource on featureActivation {
                    address: "RAI Workbench:/features/" + (index + 1) + "/activation"
                    sendUpdates: false
                  }
                  UI.AddressSource on featureDescription {
                    address: "RAI Workbench:/features/" + (index + 1) + "/description"
                    sendUpdates: false
                  }

                  RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 12

                    Label {
                      Layout.preferredWidth: 74
                      text: featureRow.featureIndex >= 0 ? "#" + featureRow.featureIndex : "—"
                      color: "#b8a5ff"
                      font.pixelSize: 14
                      font.bold: true
                    }
                    Label {
                      Layout.preferredWidth: 98
                      text: featureRow.featureActivation.toFixed(6)
                      color: "#8fe0c2"
                      font.pixelSize: 13
                    }
                    Label {
                      Layout.fillWidth: true
                      text: featureRow.featureDescription.length > 0
                        ? featureRow.featureDescription
                        : "No Neuronpedia description"
                      color: featureRow.featureDescription.length > 0 ? "#d6dde8" : "#6f7a8b"
                      font.pixelSize: 13
                      elide: Text.ElideRight
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
