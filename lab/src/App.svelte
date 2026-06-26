<script>
  const options = [
    {
      id: "scenario",
      label: "1. Try a built-in false-success scenario",
      action: "Run scenario"
    },
    {
      id: "local",
      label: "2. Scan your own repo",
      action: "Scan local repo"
    },
    {
      id: "github",
      label: "3. Scan a public GitHub repo",
      action: "Scan GitHub repo"
    }
  ];

  let selected = "scenario";
  let target = "https://github.com/org/repo";
  let result = null;
  let error = "";
  let loading = false;
  let copied = false;

  $: activeOption = options.find((option) => option.id === selected) || options[0];
  $: card = result?.card;
  $: findings = result?.report?.findings || [];
  $: topFinding = card?.top_finding;

  function selectOption(id) {
    selected = id;
    error = "";
    copied = false;
    if (id === "local") {
      target = ".";
    }
    if (id === "github") {
      target = "https://github.com/org/repo";
    }
  }

  async function runScan() {
    error = "";
    copied = false;
    loading = true;
    try {
      const endpoint = selected === "scenario" ? "/api/scenario" : "/api/scan";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: selected, target })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || "Scan failed.");
      }
      result = payload;
    } catch (scanError) {
      error = scanError.message;
    } finally {
      loading = false;
    }
  }

  async function copyReport() {
    if (!result?.markdown) {
      return;
    }
    try {
      await navigator.clipboard.writeText(result.markdown);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = result.markdown;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    copied = true;
  }
</script>

<main class="shell">
  <section class="workspace">
    <div class="masthead">
      <div>
        <p class="eyebrow">False Success Lab</p>
        <h1>Scan your agent repo, find false-success risks, then watch the gate block them.</h1>
      </div>
      <div class="status-strip" aria-label="Lab flow">
        <span>scan</span>
        <span>report</span>
        <span>gate</span>
      </div>
    </div>

    <div class="grid">
      <section class="panel controls" aria-label="Scan options">
        <div class="option-list">
          {#each options as option}
            <button
              class:active={selected === option.id}
              class="option"
              type="button"
              on:click={() => selectOption(option.id)}
            >
              <span>{option.label}</span>
            </button>
          {/each}
        </div>

        {#if selected !== "scenario"}
          <label class="field">
            <span>{selected === "github" ? "GitHub repository" : "Local repository path"}</span>
            <input
              bind:value={target}
              placeholder={selected === "github" ? "https://github.com/org/repo" : "/path/to/agent-repo"}
              spellcheck="false"
            />
          </label>
        {:else}
          <div class="scenario-box">
            <strong>Built-in scenario</strong>
            <span>Refund API accepts the request while settlement is still pending.</span>
          </div>
        {/if}

        <button class="primary" type="button" on:click={runScan} disabled={loading}>
          {loading ? "Scanning..." : activeOption.action}
        </button>

        {#if error}
          <p class="error">{error}</p>
        {/if}
      </section>

      <section class="panel report" aria-live="polite">
        {#if card}
          <div class="report-head">
            <div>
              <p class="eyebrow">False-success report card</p>
              <h2>{card.repository}</h2>
            </div>
            <button class="copy" type="button" on:click={copyReport}>
              {copied ? "Copied" : "Copy report"}
            </button>
          </div>

          <div class="metrics">
            <div>
              <span>Risky actions found</span>
              <strong>{card.risky_actions_found}</strong>
            </div>
            <div>
              <span>High severity</span>
              <strong>{card.high_severity}</strong>
            </div>
            <div>
              <span>False-success exposure</span>
              <strong>{card.false_success_exposure}</strong>
            </div>
            <div>
              <span>Confidence</span>
              <strong>{card.confidence}</strong>
            </div>
          </div>

          <div class:blocked={card.gate_label === "BLOCK"} class:review={card.gate_label === "REVIEW"} class:allow={card.gate_label === "ALLOW"} class="gate">
            <span>{card.gate_label}</span>
            <p>{card.gate_detail}</p>
          </div>

          <p class="honesty">{card.honesty_note}</p>

          {#if topFinding}
            <div class="top-finding">
              <p class="eyebrow">Top finding</p>
              <h3>{topFinding.action}</h3>
              <p>{topFinding.why}</p>
              <dl>
                <div>
                  <dt>Location</dt>
                  <dd>{topFinding.path}:{topFinding.line}</dd>
                </div>
                <div>
                  <dt>Severity</dt>
                  <dd>{topFinding.severity}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{topFinding.confidence}</dd>
                </div>
              </dl>
            </div>
          {:else}
            <div class="top-finding quiet">
              <h3>No configured finding fired.</h3>
              <p>This is still a static scan. Production actions should use runtime outcome gates.</p>
            </div>
          {/if}

          {#if findings.length}
            <div class="finding-list">
              {#each findings.slice(0, 5) as finding}
                <article class="finding">
                  <div>
                    <strong>{finding.action}</strong>
                    <span>{finding.path}:{finding.line}</span>
                  </div>
                  <span class="pill {finding.severity}">{finding.severity}</span>
                  {#if finding.confidence === "low"}
                    <p>Possible risk, needs review.</p>
                  {:else}
                    <p>{finding.why}</p>
                  {/if}
                </article>
              {/each}
            </div>
          {/if}
        {:else}
          <div class="empty">
            <p class="eyebrow">Ready</p>
            <h2>Choose an entry point to create a report card.</h2>
            <p>The lab uses the same scanner as the CLI and keeps weak findings labeled as review prompts.</p>
          </div>
        {/if}
      </section>
    </div>
  </section>
</main>
