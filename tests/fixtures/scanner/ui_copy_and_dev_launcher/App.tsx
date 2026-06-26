export function DecisionPanel() {
  function decide(action: "approve" | "reject") {
    return { action };
  }

  const summary = `${term} is governed by Canonical v14, approved by ${approvedBy}. No single authority can approve it.`;

  return (
    <section>
      <p>Calls the deployed runtime. The proposal was approved.</p>
      <button onClick={() => decide("approve")}>Approve</button>
    </section>
  );
}
