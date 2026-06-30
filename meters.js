(function() {
    function multClass(m) {
        if (m < 0.8) return 'ok';
        if (m <= 1.0) return 'warn';
        return 'over';
    }

    function calcMult(pct, resetsAt, periodHours) {
        if (!resetsAt || !pct) return null;
        var remaining = (new Date(resetsAt) - new Date()) / 3600000;
        if (remaining <= 0) return null;
        var timeLeft = (remaining / periodHours) * 100;
        var budgetLeft = 100 - pct;
        if (budgetLeft <= 0) return Infinity;
        return timeLeft / budgetLeft;
    }

    function meter(label, pct, mult, plan) {
        var cls = mult !== null ? multClass(mult) : 'ok';
        var fillW = Math.min(pct, 100);
        var multStr = mult === null ? '' : (mult >= 10 ? '>10x' : mult.toFixed(1) + 'x');
        var planStr = plan || '';
        return '<span class="meter">' +
            '<span class="meter-name">' + label + '</span>' +
            '<span class="meter-bar"><span class="meter-fill ' + cls + '" style="width:' + fillW + '%"></span><span class="meter-plan">' + planStr + '</span></span>' +
            '<span class="meter-mult ' + cls + '">' + multStr + '</span>' +
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

    var el = document.getElementById('meters');
    if (!el) return;

    fetch('/usage.json').then(function(r) { return r.json(); }).then(function(d) {
        var html = '<div class="meters-title"><span>Weekly</span><span>Burn</span></div><div class="meters-body">';

        if (d.claude && d.claude['7d']) {
            var c = d.claude;
            var m = calcMult(c['7d'].pct, c['7d'].resets_at, 168);
            html += meter('claude', c['7d'].pct, m, c.plan);
        }

        if (d.codex && d.codex['7d']) {
            var x = d.codex;
            var m = calcMult(x['7d'].pct, x['7d'].resets_at, 168);
            html += meter('codex', x['7d'].pct, m, x.plan);
        } else {
            html += meter('codex', 0, null);
        }

        if (d.agy) {
            var a = d.agy;
            var b = agyWeeklyBucket(a);
            if (b && b.remaining_pct !== null && b.remaining_pct !== undefined) {
                var pct = Math.max(0, 100 - b.remaining_pct);
                var m = calcMult(pct, b.reset_time, 168);
                html += meter('agy', pct, m, a.plan);
            }
        }

        html += '</div>';
        el.innerHTML = html;
    }).catch(function() {});
})();
