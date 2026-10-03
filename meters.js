(function() {
    function multClass(m) {
        if (m < 0.8) return 'ok';
        if (m <= 1.0) return 'warn';
        return 'over';
    }

    function calcMult(pct, resetsAt, periodHours) {
        if (!pct) return 0;
        if (!resetsAt) return null;
        var remaining = (new Date(resetsAt) - new Date()) / 3600000;
        if (remaining <= 0) return null;
        var timeLeft = (remaining / periodHours) * 100;
        var budgetLeft = 100 - pct;
        if (budgetLeft <= 0) return Infinity;
        return timeLeft / budgetLeft;
    }

    // Fill level: 1x fills to the centre tick, linear from 0x, logarithmic out to 20x at the right end.
    var MAX_MULT = 20;
    var STALE_MS = 3 * 3600000;
    function levelPosition(mult) {
        if (mult <= 1) return mult / 2;
        return 0.5 + Math.min(Math.log(mult) / Math.log(MAX_MULT), 1) / 2;
    }

    function multText(mult) {
        if (mult > MAX_MULT) return '>' + MAX_MULT + 'x';
        return mult >= 10 ? Math.round(mult) + 'x' : mult.toFixed(1) + 'x';
    }

    // Brand marks from Lobe Icons (MIT), as on the Sycophancy Bench page.
    var ICONS = {
        claude: "<svg aria-hidden=\"true\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M4.709 15.955l4.72-2.647.08-.23-.08-.128H9.2l-.79-.048-2.698-.073-2.339-.097-2.266-.122-.571-.121L0 11.784l.055-.352.48-.321.686.06 1.52.103 2.278.158 1.652.097 2.449.255h.389l.055-.157-.134-.098-.103-.097-2.358-1.596-2.552-1.688-1.336-.972-.724-.491-.364-.462-.158-1.008.656-.722.881.06.225.061.893.686 1.908 1.476 2.491 1.833.365.304.145-.103.019-.073-.164-.274-1.355-2.446-1.446-2.49-.644-1.032-.17-.619a2.97 2.97 0 01-.104-.729L6.283.134 6.696 0l.996.134.42.364.62 1.414 1.002 2.229 1.555 3.03.456.898.243.832.091.255h.158V9.01l.128-1.706.237-2.095.23-2.695.08-.76.376-.91.747-.492.584.28.48.685-.067.444-.286 1.851-.559 2.903-.364 1.942h.212l.243-.242.985-1.306 1.652-2.064.73-.82.85-.904.547-.431h1.033l.76 1.129-.34 1.166-1.064 1.347-.881 1.142-1.264 1.7-.79 1.36.073.11.188-.02 2.856-.606 1.543-.28 1.841-.315.833.388.091.395-.328.807-1.969.486-2.309.462-3.439.813-.042.03.049.061 1.549.146.662.036h1.622l3.02.225.79.522.474.638-.079.485-1.215.62-1.64-.389-3.829-.91-1.312-.329h-.182v.11l1.093 1.068 2.006 1.81 2.509 2.33.127.578-.322.455-.34-.049-2.205-1.657-.851-.747-1.926-1.62h-.128v.17l.444.649 2.345 3.521.122 1.08-.17.353-.608.213-.668-.122-1.374-1.925-1.415-2.167-1.143-1.943-.14.08-.674 7.254-.316.37-.729.28-.607-.461-.322-.747.322-1.476.389-1.924.315-1.53.286-1.9.17-.632-.012-.042-.14.018-1.434 1.967-2.18 2.945-1.726 1.845-.414.164-.717-.37.067-.662.401-.589 2.388-3.036 1.44-1.882.93-1.086-.006-.158h-.055L4.132 18.56l-1.13.146-.487-.456.061-.746.231-.243 1.908-1.312-.006.006z\" fill=\"#D97757\" fill-rule=\"nonzero\"></path></svg>",
        codex: "<svg aria-hidden=\"true\" fill=\"currentColor\" fill-rule=\"evenodd\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M9.205 8.658v-2.26c0-.19.072-.333.238-.428l4.543-2.616c.619-.357 1.356-.523 2.117-.523 2.854 0 4.662 2.212 4.662 4.566 0 .167 0 .357-.024.547l-4.71-2.759a.797.797 0 00-.856 0l-5.97 3.473zm10.609 8.8V12.06c0-.333-.143-.57-.429-.737l-5.97-3.473 1.95-1.118a.433.433 0 01.476 0l4.543 2.617c1.309.76 2.189 2.378 2.189 3.948 0 1.808-1.07 3.473-2.76 4.163zM7.802 12.703l-1.95-1.142c-.167-.095-.239-.238-.239-.428V5.899c0-2.545 1.95-4.472 4.591-4.472 1 0 1.927.333 2.712.928L8.23 5.067c-.285.166-.428.404-.428.737v6.898zM12 15.128l-2.795-1.57v-3.33L12 8.658l2.795 1.57v3.33L12 15.128zm1.796 7.23c-1 0-1.927-.332-2.712-.927l4.686-2.712c.285-.166.428-.404.428-.737v-6.898l1.974 1.142c.167.095.238.238.238.428v5.233c0 2.545-1.974 4.472-4.614 4.472zm-5.637-5.303l-4.544-2.617c-1.308-.761-2.188-2.378-2.188-3.948A4.482 4.482 0 014.21 6.327v5.423c0 .333.143.571.428.738l5.947 3.449-1.95 1.118a.432.432 0 01-.476 0zm-.262 3.9c-2.688 0-4.662-2.021-4.662-4.519 0-.19.024-.38.047-.57l4.686 2.71c.286.167.571.167.856 0l5.97-3.448v2.26c0 .19-.07.333-.237.428l-4.543 2.616c-.619.357-1.356.523-2.117.523zm5.899 2.83a5.947 5.947 0 005.827-4.756C22.287 18.339 24 15.84 24 13.296c0-1.665-.713-3.282-1.998-4.448.119-.5.19-.999.19-1.498 0-3.401-2.759-5.947-5.946-5.947-.642 0-1.26.095-1.88.31A5.962 5.962 0 0010.205 0a5.947 5.947 0 00-5.827 4.757C1.713 5.447 0 7.945 0 10.49c0 1.666.713 3.283 1.998 4.448-.119.5-.19 1-.19 1.499 0 3.401 2.759 5.946 5.946 5.946.642 0 1.26-.095 1.88-.309a5.96 5.96 0 004.162 1.713z\"></path></svg>",
        agy: "<svg aria-hidden=\"true\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"#3186FF\"></path><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"url(#lobe-icons-gemini-0-_R_0_)\"></path><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"url(#lobe-icons-gemini-1-_R_0_)\"></path><path d=\"M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z\" fill=\"url(#lobe-icons-gemini-2-_R_0_)\"></path><defs><linearGradient gradientUnits=\"userSpaceOnUse\" id=\"lobe-icons-gemini-0-_R_0_\" x1=\"7\" x2=\"11\" y1=\"15.5\" y2=\"12\"><stop stop-color=\"#08B962\"></stop><stop offset=\"1\" stop-color=\"#08B962\" stop-opacity=\"0\"></stop></linearGradient><linearGradient gradientUnits=\"userSpaceOnUse\" id=\"lobe-icons-gemini-1-_R_0_\" x1=\"8\" x2=\"11.5\" y1=\"5.5\" y2=\"11\"><stop stop-color=\"#F94543\"></stop><stop offset=\"1\" stop-color=\"#F94543\" stop-opacity=\"0\"></stop></linearGradient><linearGradient gradientUnits=\"userSpaceOnUse\" id=\"lobe-icons-gemini-2-_R_0_\" x1=\"3.5\" x2=\"17.5\" y1=\"13.5\" y2=\"12\"><stop stop-color=\"#FABC12\"></stop><stop offset=\".46\" stop-color=\"#FABC12\" stop-opacity=\"0\"></stop></linearGradient></defs></svg>",
        zcode: "<svg aria-hidden=\"true\" fill=\"currentColor\" fill-rule=\"evenodd\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M12.105 2L9.927 4.953H.653L2.83 2h9.276zM23.254 19.048L21.078 22h-9.242l2.174-2.952h9.244zM24 2L9.264 22H0L14.736 2H24z\"></path></svg>"
    };
    var NAMES = { claude: 'Claude', codex: 'Codex', agy: 'Antigravity', zcode: 'Z.ai' };

    function meter(key, mult, plan, note) {
        var cls = mult !== null ? multClass(mult) : 'ok';
        var fill = mult === null ? '' :
            '<span class="meter-fill ' + cls + '" style="width:' + (levelPosition(mult) * 100).toFixed(1) + '%"></span>';
        return '<span class="meter' + (note ? ' muted' : '') + '" title="' + NAMES[key] + (note ? ': ' + note : '') + '">' +
            '<span class="meter-icon ' + key + '" role="img" aria-label="' + NAMES[key] + '">' + ICONS[key] + '</span>' +
            '<span class="meter-bar"><span class="meter-center"></span>' + fill +
            '<span class="meter-plan">' + (note === 'unavailable' ? 'unavailable' : plan || '') + '</span></span>' +
            '<span class="meter-mult ' + cls + '">' + (mult === null ? '–' : multText(mult)) + '</span>' +
            '</span>';
    }

    // A quota whose own data is old gets no reading: a burn computed from old usage would be wrong.
    function staleNote(data) {
        var updated = Date.parse(data && data.updated_at);
        if (!updated || new Date() - updated <= STALE_MS) return null;
        return 'no data since ' + new Date(updated).toLocaleString();
    }

    function reading(key, data, mult) {
        var note = staleNote(data);
        return note ? meter(key, null, data.plan, note) : meter(key, mult, data.plan);
    }

    function agyWeeklyBucket(data) {
        var groups = data.quota_summary && data.quota_summary.groups;
        if (!groups) return null;
        for (var i = 0; i < groups.length; i++) {
            var group = groups[i];
            if (String(group.display_name || '').toLowerCase().indexOf('gemini') < 0) continue;
            var buckets = group.buckets || [];
            for (var j = 0; j < buckets.length; j++) {
                var bucket = buckets[j];
                var win = String(bucket.window || '').toLowerCase();
                var name = String(bucket.display_name || '').toLowerCase();
                if (win === 'weekly' || win === '1w' || win === '7d' || name.indexOf('weekly') >= 0) {
                    return bucket;
                }
            }
        }
        return null;
    }

    function codexWindowSeconds(bucket, fallback) {
        var seconds = Number(bucket && bucket.window_secs);
        return isFinite(seconds) && seconds > 0 ? seconds : fallback;
    }

    function codexWeeklyBucket(data) {
        var modern = data.schema_version >= 2 || data.primary || data.secondary;
        var specs = modern
            ? [['primary', null], ['secondary', null]]
            : [['5h', 18000], ['7d', 604800]];
        for (var i = 0; i < specs.length; i++) {
            var bucket = data[specs[i][0]];
            if (!bucket) continue;
            var seconds = codexWindowSeconds(bucket, specs[i][1]);
            if (seconds && Math.abs(seconds - 604800) / 604800 <= 0.1) return bucket;
        }
        return null;
    }

    function zcodeWeeklyBucket(data) {
        var limits = data.limits || [];
        for (var i = 0; i < limits.length; i++) {
            if (limits[i].unit === 6 && limits[i].number === 1 && limits[i].pct !== null && limits[i].pct !== undefined) return limits[i];
        }
        return null;
    }

    function claudeUnavailable(data) {
        return data && data.status === 'unavailable' && data.unavailable;
    }

    var el = document.getElementById('meters');
    if (!el) return;

    fetch('/usage.json').then(function(r) { return r.json(); }).then(function(d) {
        var html = '<div class="meters-title"><span>Weekly</span><span>Burn</span></div><div class="meters-body">';

        if (claudeUnavailable(d.claude)) {
            html += meter('claude', null, d.claude.plan, 'unavailable');
        } else if (d.claude && d.claude['7d']) {
            var c = d.claude;
            html += reading('claude', c, calcMult(c['7d'].pct, c['7d'].resets_at, 168));
        }

        var b = d.codex && codexWeeklyBucket(d.codex);
        if (b) {
            html += reading('codex', d.codex, calcMult(b.pct, b.resets_at, codexWindowSeconds(b, 604800) / 3600));
        } else {
            html += meter('codex', null);
        }

        b = d.agy && agyWeeklyBucket(d.agy);
        if (b && b.remaining_pct !== null && b.remaining_pct !== undefined) {
            html += reading('agy', d.agy, calcMult(Math.max(0, 100 - b.remaining_pct), b.reset_time, 168));
        }

        // Z.ai appears only while a Coding Plan is active; the daemon records an unsubscribed account as no_plan.
        b = d.zcode && d.zcode.status !== 'no_plan' && zcodeWeeklyBucket(d.zcode);
        if (b) {
            html += reading('zcode', d.zcode, calcMult(b.pct, b.resets_at, 168));
        }

        html += '</div>';
        el.innerHTML = html;
    }).catch(function() {});
})();
