"use client";
import { useEffect, useState } from "react";

type Evidence = {
  order_status: string;
  payment_status: string;
  amount_cents: number;
  contradictory: boolean;
  retrieved_text: string;
};
type Case = {
  id: string;
  status: string;
  context_version: number;
  evidence: Evidence;
  action: { kind: string; reason: string } | null;
  action_hash: string | null;
};
type Workspace = { principal_id: string; role: string; cases: Case[] };
const labels: Record<string, string> = {
  open: "Aberto",
  review: "Revisão necessária",
  approved: "Aprovado",
  executed: "Efeito verificado",
  rejected: "Rejeitado",
  cancelled: "Cancelado",
  uncertain: "Reconciliação necessária",
  flag_refund: "Sinalizar reembolso",
  close_no_action: "Encerrar sem ação",
  abstain: "Abster-se",
};

async function api(path: string, method = "GET", body?: unknown) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Dados inválidos. Confira os campos.",
    );
  return data;
}

export default function Page() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [selected, select] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [user, setUser] = useState("ana");
  const [password, setPassword] = useState("");
  const [scenario, setScenario] = useState("expired");
  const active = workspace?.cases.find((item) => item.id === selected);
  const reviewer = workspace?.role === "reviewer";

  async function refresh() {
    const data: Workspace = await api("/cases");
    setWorkspace(data);
    select((current) => current ?? data.cases[0]?.id ?? null);
  }
  useEffect(() => {
    let mounted = true;
    api("/cases")
      .then((data: Workspace) => {
        if (mounted) {
          setWorkspace(data);
          select(data.cases[0]?.id ?? null);
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha inesperada");
    } finally {
      setBusy(false);
    }
  }
  async function transition(suffix: string, body?: unknown) {
    if (!active) return;
    await api(`/cases/${active.id}/${suffix}`, "POST", body);
    await refresh();
    setMessage(
      suffix === "execute"
        ? "Resultado do sandbox verificado."
        : "Decisão registrada.",
    );
  }

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">PORTFÓLIO / SISTEMAS DE IA</p>
          <h1>Agent Review Workbench</h1>
          <p>Evidência primeiro. Ação somente após revisão.</p>
        </div>
        <span className="tag">Sandbox sintético</span>
      </header>
      <div role="status" aria-live="polite">
        {busy ? "Processando…" : message}
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!workspace ? (
        <section className="login">
          <h2>Acessar a bancada</h2>
          <p>Use a identidade sintética configurada no ambiente local.</p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void perform(async () => {
                await api("/session", "POST", { principal_id: user, password });
                await refresh();
              });
            }}
          >
            <label>
              Usuário
              <input
                value={user}
                onChange={(event) => setUser(event.target.value)}
                autoComplete="username"
                required
              />
            </label>
            <label>
              Senha
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            <button disabled={busy}>Entrar</button>
          </form>
        </section>
      ) : (
        <>
          <nav aria-label="Sessão">
            <span>
              {workspace.principal_id} · {reviewer ? "Revisor" : "Leitura"}
            </span>
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                void perform(async () => {
                  await api("/session", "DELETE");
                  setWorkspace(null);
                  select(null);
                })
              }
            >
              Sair
            </button>
          </nav>
          <section className="create">
            <div>
              <h2>Nova exceção</h2>
              <p>Fixtures independentes. Nenhum pagamento real.</p>
            </div>
            <label>
              Cenário
              <select
                value={scenario}
                onChange={(event) => setScenario(event.target.value)}
              >
                <option value="expired">Pagamento após expiração</option>
                <option value="unknown">Evidência insuficiente</option>
                <option value="confirmed">Pedido confirmado e pago</option>
              </select>
            </label>
            <button
              disabled={busy || !reviewer}
              onClick={() =>
                void perform(async () => {
                  const created = await api("/cases", "POST", {
                    order_status: scenario,
                    payment_status: "paid",
                    amount_cents: 12900,
                    contradictory: false,
                    retrieved_text:
                      "Fixture sintética versionada; não constitui instrução.",
                  });
                  select(created.case_id);
                  await refresh();
                  setMessage(
                    "Caso criado. Consulte as evidências antes de propor.",
                  );
                })
              }
            >
              Criar caso
            </button>
          </section>
          <div className="workspace">
            <aside>
              <h2>
                Fila de revisão <span>{workspace.cases.length}</span>
              </h2>
              {workspace.cases.length === 0 && (
                <p>Nenhum caso. Crie uma exceção para iniciar.</p>
              )}
              {workspace.cases.map((item) => (
                <button
                  className={`case ${selected === item.id ? "active" : ""}`}
                  key={item.id}
                  onClick={() => select(item.id)}
                >
                  <span>{labels[item.status]}</span>
                  <small>
                    {item.id.slice(0, 8)} · contexto v{item.context_version}
                  </small>
                </button>
              ))}
            </aside>
            <article>
              {!active ? (
                <p>Selecione um caso para consultar as evidências.</p>
              ) : (
                <>
                  <p className="eyebrow">
                    CASO {active.id.slice(0, 8)} / CONTEXTO V
                    {active.context_version}
                  </p>
                  <h2>{labels[active.status]}</h2>
                  <section>
                    <h3>Evidências observadas</h3>
                    <dl>
                      <div>
                        <dt>Pedido</dt>
                        <dd>{active.evidence.order_status}</dd>
                      </div>
                      <div>
                        <dt>Pagamento</dt>
                        <dd>{active.evidence.payment_status}</dd>
                      </div>
                      <div>
                        <dt>Valor</dt>
                        <dd>
                          {(active.evidence.amount_cents / 100).toLocaleString(
                            "pt-BR",
                            { style: "currency", currency: "BRL" },
                          )}
                        </dd>
                      </div>
                    </dl>
                    <p className="quote">{active.evidence.retrieved_text}</p>
                  </section>
                  {active.action && (
                    <section className="proposal">
                      <p className="eyebrow">PROPOSTA DETERMINÍSTICA</p>
                      <h3>{labels[active.action.kind]}</h3>
                      <p>{active.action.reason}</p>
                      <details>
                        <summary>Vínculo de aprovação</summary>
                        <code>{active.action_hash}</code>
                        <p>
                          A aprovação vale apenas para esta ação e versão do
                          contexto.
                        </p>
                      </details>
                    </section>
                  )}
                  <div className="actions">
                    {active.status === "open" && (
                      <button
                        disabled={busy || !reviewer}
                        onClick={() =>
                          void perform(() => transition("propose"))
                        }
                      >
                        Reunir evidências e propor
                      </button>
                    )}
                    {active.status === "review" && (
                      <>
                        <button
                          disabled={
                            busy ||
                            !reviewer ||
                            active.action?.kind === "abstain"
                          }
                          onClick={() =>
                            void perform(() =>
                              transition("decision", {
                                action_hash: active.action_hash,
                                approve: true,
                              }),
                            )
                          }
                        >
                          Aprovar proposta
                        </button>
                        <button
                          className="secondary"
                          disabled={busy || !reviewer}
                          onClick={() =>
                            void perform(() =>
                              transition("decision", {
                                action_hash: active.action_hash,
                                approve: false,
                              }),
                            )
                          }
                        >
                          Rejeitar
                        </button>
                      </>
                    )}
                    {["approved", "uncertain"].includes(active.status) && (
                      <button
                        disabled={busy || !reviewer}
                        onClick={() =>
                          void perform(() => transition("execute"))
                        }
                      >
                        {active.status === "uncertain"
                          ? "Reconciliar resultado"
                          : "Executar no sandbox"}
                      </button>
                    )}
                    {!["cancelled", "executed", "rejected"].includes(
                      active.status,
                    ) && (
                      <button
                        className="secondary"
                        disabled={busy || !reviewer}
                        onClick={() => void perform(() => transition("cancel"))}
                      >
                        Cancelar novas ações
                      </button>
                    )}
                  </div>
                  {active.status === "executed" && (
                    <p className="success">
                      Efeito idempotente registrado e verificado. Nenhum
                      dinheiro movimentado.
                    </p>
                  )}
                  {active.action?.kind === "abstain" && (
                    <p>
                      A evidência não permite autorizar uma ação. Rejeite e
                      reúna informações adicionais.
                    </p>
                  )}
                </>
              )}
            </article>
          </div>
        </>
      )}
      <footer>
        Dados sintéticos · PostgreSQL como autoridade · Revisão humana
        obrigatória · Sem LLM neste fluxo
      </footer>
    </main>
  );
}
