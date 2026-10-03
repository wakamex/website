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

    // Spirit-level position: 1x is the centre line, linear from 0x on the left, logarithmic out to 20x on the right.
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

    function meter(label, mult, note) {
        var cls = mult !== null ? multClass(mult) : 'ok';
        var bubble = mult === null ? '' :
            '<span class="meter-bubble ' + cls + '" style="left:calc(6px + (100% - 12px) * ' + levelPosition(mult) + ')"></span>';
        return '<span class="meter">' +
            '<span class="meter-name">' + label + '</span>' +
            '<span class="meter-bar"><span class="meter-center"></span>' + bubble +
            (note ? '<span class="meter-plan">' + note + '</span>' : '') + '</span>' +
            '<span class="meter-mult ' + cls + '">' + (mult === null ? '' : multText(mult)) + '</span>' +
            '</span>';
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

    function claudeUnavailable(data) {
        return data && data.status === 'unavailable' && data.unavailable;
    }

    var el = document.getElementById('meters');
    if (!el) return;

    fetch('/usage.json').then(function(r) { return r.json(); }).then(function(d) {
        var html = '<div class="meters-title"><span>Weekly</span><span>Burn</span></div><div class="meters-body">';

        if (claudeUnavailable(d.claude)) {
            html += meter('claude', null, 'unavailable');
        } else if (d.claude && d.claude['7d']) {
            var c = d.claude;
            html += meter('claude', calcMult(c['7d'].pct, c['7d'].resets_at, 168));
        }

        if (d.codex && codexWeeklyBucket(d.codex)) {
            var x = d.codex;
            var b = codexWeeklyBucket(x);
            var periodHours = codexWindowSeconds(b, 604800) / 3600;
            html += meter('codex', calcMult(b.pct, b.resets_at, periodHours));
        } else {
            html += meter('codex', null);
        }

        if (d.agy) {
            var a = d.agy;
            var b = agyWeeklyBucket(a);
            if (b && b.remaining_pct !== null && b.remaining_pct !== undefined) {
                var pct = Math.max(0, 100 - b.remaining_pct);
                html += meter('agy', calcMult(pct, b.reset_time, 168));
            }
        }

        html += '</div>';
        el.innerHTML = html;

        // Dim the widget when the publisher has stopped delivering fresh data.
        var newest = 0;
        ['claude', 'codex', 'agy'].forEach(function(key) {
            var updated = d[key] && Date.parse(d[key].updated_at);
            if (updated > newest) newest = updated;
        });
        if (newest && new Date() - newest > STALE_MS) {
            el.classList.add('stale');
            el.title = 'Usage data last updated ' + new Date(newest).toLocaleString();
        }
    }).catch(function() {});
})();
