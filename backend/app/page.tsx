export default function HomePage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>FairServe</h1>
      <p>Demo UI for fairness, policy, and review flows.</p>
      <ul>
        <li>
          <a href="/intake">Intake Summary</a>
        </li>
        <li>
          <a href="/fairness">Fairness Leaderboard</a>
        </li>
        <li>
          <a href="/policy">Policy Generation</a>
        </li>
        <li>
          <a href="/review">Simulation Review</a>
        </li>
      </ul>
    </main>
  );
}
