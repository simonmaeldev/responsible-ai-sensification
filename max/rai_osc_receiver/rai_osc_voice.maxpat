{
  "patcher": {
    "fileversion": 1,
    "appversion": {
      "major": 9,
      "minor": 1,
      "revision": 4,
      "architecture": "x64",
      "modernui": 1
    },
    "classnamespace": "box",
    "rect": [100.0, 100.0, 760.0, 520.0],
    "openinpresentation": 0,
    "default_fontsize": 12.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [15.0, 15.0],
    "boxes": [
      {
        "box": {
          "id": "obj-in",
          "maxclass": "newobj",
          "text": "in 1",
          "numinlets": 0,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [45.0, 35.0, 30.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-route",
          "maxclass": "newobj",
          "text": "route note sustain off",
          "numinlets": 1,
          "numoutlets": 4,
          "outlettype": ["", "", "", ""],
          "patching_rect": [45.0, 80.0, 150.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-note-trigger",
          "maxclass": "newobj",
          "text": "t l b",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["list", "bang"],
          "patching_rect": [45.0, 125.0, 42.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-note-unpack",
          "maxclass": "newobj",
          "text": "unpack 0. 0. 0.",
          "numinlets": 1,
          "numoutlets": 3,
          "outlettype": ["float", "float", "float"],
          "patching_rect": [45.0, 170.0, 105.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-sustain-trigger",
          "maxclass": "newobj",
          "text": "t l b",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["list", "bang"],
          "patching_rect": [235.0, 125.0, 42.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-sustain-unpack",
          "maxclass": "newobj",
          "text": "unpack 0. 0.",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["float", "float"],
          "patching_rect": [235.0, 170.0, 85.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-freq-trigger",
          "maxclass": "newobj",
          "text": "t b f",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["bang", "float"],
          "patching_rect": [45.0, 220.0, 42.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-freq-clip",
          "maxclass": "newobj",
          "text": "clip 20. 20000.",
          "numinlets": 3,
          "numoutlets": 1,
          "outlettype": ["float"],
          "patching_rect": [125.0, 260.0, 100.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-gain-clip",
          "maxclass": "newobj",
          "text": "clip 0. 0.12",
          "numinlets": 3,
          "numoutlets": 1,
          "outlettype": ["float"],
          "patching_rect": [275.0, 220.0, 85.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-attack",
          "maxclass": "message",
          "text": "$1 5",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [275.0, 260.0, 45.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-delay",
          "maxclass": "newobj",
          "text": "delay 450",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": ["bang"],
          "patching_rect": [45.0, 305.0, 65.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-stop",
          "maxclass": "message",
          "text": "stop",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [185.0, 125.0, 38.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-off-trigger",
          "maxclass": "newobj",
          "text": "t b b",
          "numinlets": 1,
          "numoutlets": 2,
          "outlettype": ["bang", "bang"],
          "patching_rect": [380.0, 125.0, 42.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-release",
          "maxclass": "message",
          "text": "0. 25",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": [""],
          "patching_rect": [380.0, 260.0, 48.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-cycle",
          "maxclass": "newobj",
          "text": "cycle~ 440.",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": ["signal"],
          "patching_rect": [125.0, 350.0, 72.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-line",
          "maxclass": "newobj",
          "text": "line~ 0.",
          "numinlets": 2,
          "numoutlets": 2,
          "outlettype": ["signal", "bang"],
          "patching_rect": [275.0, 350.0, 55.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-multiply",
          "maxclass": "newobj",
          "text": "*~",
          "numinlets": 2,
          "numoutlets": 1,
          "outlettype": ["signal"],
          "patching_rect": [185.0, 395.0, 32.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-hard-clip",
          "maxclass": "newobj",
          "text": "clip~ -0.12 0.12",
          "numinlets": 3,
          "numoutlets": 1,
          "outlettype": ["signal"],
          "patching_rect": [185.0, 435.0, 105.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-out",
          "maxclass": "newobj",
          "text": "out~ 1",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [185.0, 475.0, 42.0, 22.0]
        }
      }
    ],
    "lines": [
      {"patchline": {"source": ["obj-in", 0], "destination": ["obj-route", 0]}},
      {"patchline": {"source": ["obj-route", 0], "destination": ["obj-note-trigger", 0]}},
      {"patchline": {"source": ["obj-note-trigger", 0], "destination": ["obj-note-unpack", 0]}},
      {"patchline": {"source": ["obj-note-trigger", 1], "destination": ["obj-stop", 0]}},
      {"patchline": {"source": ["obj-route", 1], "destination": ["obj-sustain-trigger", 0]}},
      {"patchline": {"source": ["obj-sustain-trigger", 0], "destination": ["obj-sustain-unpack", 0]}},
      {"patchline": {"source": ["obj-sustain-trigger", 1], "destination": ["obj-stop", 0]}},
      {"patchline": {"source": ["obj-route", 2], "destination": ["obj-off-trigger", 0]}},
      {"patchline": {"source": ["obj-off-trigger", 0], "destination": ["obj-release", 0]}},
      {"patchline": {"source": ["obj-off-trigger", 1], "destination": ["obj-stop", 0]}},
      {"patchline": {"source": ["obj-stop", 0], "destination": ["obj-delay", 0]}},
      {"patchline": {"source": ["obj-note-unpack", 2], "destination": ["obj-delay", 1]}},
      {"patchline": {"source": ["obj-note-unpack", 1], "destination": ["obj-gain-clip", 0]}},
      {"patchline": {"source": ["obj-note-unpack", 0], "destination": ["obj-freq-trigger", 0]}},
      {"patchline": {"source": ["obj-freq-trigger", 0], "destination": ["obj-delay", 0]}},
      {"patchline": {"source": ["obj-freq-trigger", 1], "destination": ["obj-freq-clip", 0]}},
      {"patchline": {"source": ["obj-sustain-unpack", 1], "destination": ["obj-gain-clip", 0]}},
      {"patchline": {"source": ["obj-sustain-unpack", 0], "destination": ["obj-freq-clip", 0]}},
      {"patchline": {"source": ["obj-gain-clip", 0], "destination": ["obj-attack", 0]}},
      {"patchline": {"source": ["obj-attack", 0], "destination": ["obj-line", 0]}},
      {"patchline": {"source": ["obj-delay", 0], "destination": ["obj-release", 0]}},
      {"patchline": {"source": ["obj-release", 0], "destination": ["obj-line", 0]}},
      {"patchline": {"source": ["obj-freq-clip", 0], "destination": ["obj-cycle", 0]}},
      {"patchline": {"source": ["obj-cycle", 0], "destination": ["obj-multiply", 0]}},
      {"patchline": {"source": ["obj-line", 0], "destination": ["obj-multiply", 1]}},
      {"patchline": {"source": ["obj-multiply", 0], "destination": ["obj-hard-clip", 0]}},
      {"patchline": {"source": ["obj-hard-clip", 0], "destination": ["obj-out", 0]}}
    ]
  }
}
