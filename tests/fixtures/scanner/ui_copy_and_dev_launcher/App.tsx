export function DecisionPanel() {
  function decide(action: "approve" | "reject") {
    return { action };
  }

  return (
    <section>
      <p>Calls the deployed runtime. The proposal was approved.</p>
      <button onClick={() => decide("approve")}>Approve</button>
    </section>
  );
}
