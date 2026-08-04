autowatch = 1;
inlets = 1;
outlets = 0;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

var values = {
    state: "listening",
    run_state: "idle",
    port: 9000,
    run_id: "-",
    sequence: -1,
    token_text: "-",
    note_count: 0,
    tonality: "-",
    bpm: 120,
    mode: "timed",
    loop: 0,
    tonality_enabled: 0,
    prompt_influence: 0.0,
    pitch_bias: 0.0,
    last_frequency: 0.0,
    last_activation: 0.0,
    last_feature: -1,
    last_cluster: -1,
    last_instrument: "-",
    last_error: "none",
    unknown_count: 0,
    release_count: 0,
    last_release_reason: "none"
};

function anything() {
    var name = String(messagename);
    var args = arrayfromargs(arguments);
    if (args.length === 0) {
        values[name] = "-";
    } else if (args.length === 1) {
        values[name] = args[0];
    } else {
        values[name] = args.join(" ");
    }
    mgraphics.redraw();
}

function paint() {
    var width = box.rect[2] - box.rect[0];
    var height = box.rect[3] - box.rect[1];
    var receiving = String(values.state) === "receiving";
    var hasError = String(values.last_error) !== "none";

    mgraphics.set_source_rgba(0.055, 0.06, 0.075, 1.0);
    mgraphics.rectangle(0, 0, width, height);
    mgraphics.fill();

    mgraphics.set_source_rgba(receiving ? 0.20 : 0.95, receiving ? 0.82 : 0.65, receiving ? 0.48 : 0.18, 1.0);
    mgraphics.rectangle(0, 0, 7, height);
    mgraphics.fill();

    drawText("RAI OSC RECEIVER", 20, 26, 16, [0.92, 0.94, 1.0, 1.0]);
    drawText(String(values.state).toUpperCase() + " UDP " + values.port, 20, 50, 12,
        receiving ? [0.30, 0.95, 0.58, 1.0] : [1.0, 0.72, 0.30, 1.0]);

    var left = [
        ["Run", values.run_id],
        ["Run state", values.run_state],
        ["Sequence", values.sequence],
        ["Token", truncate(values.token_text, 46)],
        ["Notes", values.note_count],
        ["Tonality", values.tonality]
    ];
    var right = [
        ["BPM", values.bpm],
        ["Mode", values.mode],
        ["Loop", values.loop],
        ["Tonality enabled", values.tonality_enabled],
        ["Prompt influence", formatNumber(values.prompt_influence, 3)],
        ["Pitch bias", formatNumber(values.pitch_bias, 3)]
    ];

    drawColumn(left, 20, 84, Math.max(280, width * 0.48));
    drawColumn(right, Math.max(360, width * 0.52), 84, width - 20);

    var metadataY = 242;
    drawText("LATEST RAW NOTE", 20, metadataY, 11, [0.55, 0.67, 0.90, 1.0]);
    drawText(
        "Hz " + formatNumber(values.last_frequency, 6) +
        "   activation " + formatNumber(values.last_activation, 6) +
        "   feature " + values.last_feature +
        "   cluster " + values.last_cluster +
        "   instrument " + values.last_instrument,
        20, metadataY + 24, 11, [0.86, 0.88, 0.92, 1.0]);

    drawText(
        "Unknown ignored: " + values.unknown_count +
        "   Voice releases: " + values.release_count +
        "   Last release: " + values.last_release_reason,
        20, metadataY + 52, 10, [0.62, 0.66, 0.73, 1.0]);

    drawText("LAST ERROR", 20, metadataY + 82, 11,
        hasError ? [1.0, 0.42, 0.42, 1.0] : [0.45, 0.72, 0.55, 1.0]);
    drawText(truncate(values.last_error, 108), 20, metadataY + 106, 10,
        hasError ? [1.0, 0.68, 0.68, 1.0] : [0.64, 0.70, 0.67, 1.0]);
}

function drawColumn(rows, x, y, rightEdge) {
    var i;
    for (i = 0; i < rows.length; i += 1) {
        var rowY = y + (i * 25);
        drawText(rows[i][0], x, rowY, 10, [0.48, 0.55, 0.67, 1.0]);
        drawText(truncate(rows[i][1], 42), x + 112, rowY, 11, [0.90, 0.92, 0.97, 1.0]);
    }
}

function drawText(text, x, y, size, color) {
    mgraphics.select_font_face("Arial", "normal", "normal");
    mgraphics.set_font_size(size);
    mgraphics.set_source_rgba(color[0], color[1], color[2], color[3]);
    mgraphics.move_to(x, y);
    mgraphics.show_text(String(text));
}

function truncate(value, limit) {
    var text = String(value);
    if (text.length <= limit) {
        return text;
    }
    return text.substring(0, Math.max(0, limit - 3)) + "...";
}

function formatNumber(value, digits) {
    var number = Number(value);
    return isFinite(number) ? number.toFixed(digits) : String(value);
}

function onresize() {
    mgraphics.redraw();
}
