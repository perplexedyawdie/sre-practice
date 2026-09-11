"""Streamlit entry point for the local e-commerce SRE learning lab."""

from __future__ import annotations

from pathlib import Path

import requests
import streamlit as st

from bank import (
    BankValidationError,
    QuestionBank,
    Scenario,
    choose_scenario,
    load_bank,
    load_bank_text,
    score_rubric,
    validate_bank_against_flags,
)
from flag_manager import (
    ActiveScenarioError,
    FlagManager,
    FlagManagerError,
    LabConfig,
    RestoreConflictError,
)
from progress import ProgressStore


APP_DIR = Path(__file__).resolve().parent
BANK_DIR = APP_DIR / "question_banks"


@st.cache_data(ttl=5, show_spinner=False)
def flag_api_health(flag_api_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"{flag_api_url}/read", timeout=2)
        response.raise_for_status()
        payload = response.json()
        count = len(payload.get("flags", {}))
        if not count:
            return False, "Flag API returned no flags"
        return True, f"Astronomy Shop connected · {count} flags available"
    except (requests.RequestException, ValueError) as exc:
        return False, f"Study mode · flag API unavailable: {exc}"


def load_selected_bank() -> QuestionBank:
    bank_paths = sorted(BANK_DIR.glob("*.yaml"))
    if not bank_paths:
        raise BankValidationError([f"No YAML banks found in {BANK_DIR}"])
    selected_name = st.sidebar.selectbox("Local question bank", [path.name for path in bank_paths])
    uploaded = st.sidebar.file_uploader("Or upload a question bank", type=["yaml", "yml"])
    if uploaded is not None:
        try:
            return load_bank_text(uploaded.getvalue().decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise BankValidationError([f"Uploaded bank is not UTF-8: {exc}"]) from exc
    return load_bank(BANK_DIR / selected_name)


def select_scenario(bank: QuestionBank, completed: set[str]) -> tuple[str, Scenario]:
    level_titles = {level.title: level.id for level in bank.levels}
    selected_level_title = st.sidebar.selectbox("Learning level", list(level_titles))
    level_id = level_titles[selected_level_title]
    candidates = bank.scenarios_for_level(level_id)

    picker_key = f"picker:{bank.id}:{level_id}"
    valid_ids = {scenario.id for scenario in candidates}
    if st.session_state.get(picker_key) not in valid_ids:
        st.session_state[picker_key] = choose_scenario(bank, level_id, completed).id

    labels = {
        scenario.id: f"{'✓' if scenario.id in completed else '○'} {scenario.title}"
        for scenario in candidates
    }
    ids = [scenario.id for scenario in candidates]
    selected_id = st.sidebar.selectbox(
        "Exercise",
        ids,
        format_func=lambda scenario_id: labels[scenario_id],
        key=picker_key,
    )

    def pick_another() -> None:
        pool_completed = set(completed)
        pool_completed.add(st.session_state[picker_key])
        st.session_state[picker_key] = choose_scenario(bank, level_id, pool_completed).id

    st.sidebar.button(
        "Pick another incomplete exercise",
        on_click=pick_another,
        use_container_width=True,
    )
    return level_id, bank.scenario(selected_id)


def render_reliability_contract(scenario: Scenario) -> None:
    st.subheader("Reliability contract")
    st.caption("These are hypothetical training targets, not production commitments.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Critical user journey**")
        st.write(scenario.critical_user_journey)
        st.markdown("**Service tier**")
        st.write(scenario.service_tier)
        st.markdown("**SLA**")
        for key, value in scenario.sla.items():
            st.write(f"{key.replace('_', ' ').title()}: {value}")
    with right:
        st.markdown("**Internal SLOs**")
        for slo in scenario.slos:
            st.write(f"• {slo.get('indicator', 'Objective')}: {slo.get('target', '')}")
        st.markdown("**Error budget**")
        st.write(scenario.error_budget)

    st.markdown("**SLIs**")
    for sli in scenario.slis:
        st.write(f"{sli.get('name', 'SLI')}: {sli.get('formula', '')}")
        if sli.get("boundary"):
            st.caption(f"Measurement boundary: {sli['boundary']}")


def render_lab_controls(
    bank: QuestionBank,
    scenario: Scenario,
    manager: FlagManager,
    live_ok: bool,
    bank_compatible: bool,
) -> None:
    st.subheader("Live lab")
    active = manager.active_session()
    if active:
        st.warning(
            f"Active fault session: **{active.get('scenario_id', 'unknown')}**. "
            "End and restore it before activating another scenario."
        )
        left, right = st.columns(2)
        if left.button("End scenario and restore flags", type="primary", use_container_width=True):
            try:
                manager.restore()
                st.session_state.pop("restore_conflict", None)
                flag_api_health.clear()
                st.success("Original feature flags restored.")
                st.rerun()
            except RestoreConflictError:
                st.session_state["restore_conflict"] = True
            except FlagManagerError as exc:
                st.error(str(exc))
        if right.button("Emergency restore", use_container_width=True):
            try:
                manager.restore(force=True)
                st.session_state.pop("restore_conflict", None)
                flag_api_health.clear()
                st.success("Original feature flags force-restored.")
                st.rerun()
            except FlagManagerError as exc:
                st.error(str(exc))

        if st.session_state.get("restore_conflict"):
            st.error("The live flags changed outside this app after activation. Restoring now would overwrite those changes.")
            force_col, keep_col = st.columns(2)
            if force_col.button("Force original snapshot", use_container_width=True):
                try:
                    manager.restore(force=True)
                    st.session_state.pop("restore_conflict", None)
                    flag_api_health.clear()
                    st.rerun()
                except FlagManagerError as exc:
                    st.error(str(exc))
            if keep_col.button("Keep current flags and close session", use_container_width=True):
                try:
                    manager.keep_current_and_close()
                    st.session_state.pop("restore_conflict", None)
                    st.rerun()
                except FlagManagerError as exc:
                    st.error(str(exc))
        return

    if not live_ok:
        st.info("Start Astronomy Shop to activate faults. You can continue reading and answering in study mode.")
    elif not bank_compatible:
        st.error("This bank does not match the local feature-flag document, so live activation is disabled.")

    if st.button(
        "Activate hidden scenario",
        type="primary",
        disabled=not live_ok or not bank_compatible,
        use_container_width=True,
    ):
        try:
            manager.activate(bank, scenario)
            flag_api_health.clear()
            st.success(f"Scenario activated. Observe the system for about {scenario.observation_minutes} minutes.")
            st.rerun()
        except (ActiveScenarioError, FlagManagerError, BankValidationError) as exc:
            st.error(str(exc))
    st.caption("Activation snapshots your current flags, turns off bank-managed faults, and applies only this hidden scenario.")


def render_investigation(scenario: Scenario, record: dict[str, object]) -> dict[str, str]:
    st.subheader("Your investigation")
    for index, task in enumerate(scenario.tasks, start=1):
        st.write(f"{index}. {task}")

    previous_answers = record.get("answers", {}) if isinstance(record.get("answers"), dict) else {}
    prefix = f"answers:{scenario.id}"
    answers = {
        "observations": st.text_area(
            "What did you observe?",
            value=str(previous_answers.get("observations", "")),
            height=120,
            key=f"{prefix}:observations",
        ),
        "diagnosis": st.text_area(
            "What is your diagnosis and evidence chain?",
            value=str(previous_answers.get("diagnosis", "")),
            height=140,
            key=f"{prefix}:diagnosis",
        ),
        "promql": st.text_area(
            "PromQL or telemetry queries you used",
            value=str(previous_answers.get("promql", "")),
            height=120,
            key=f"{prefix}:promql",
        ),
        "response": st.text_area(
            "What is your response and remediation plan?",
            value=str(previous_answers.get("response", "")),
            height=120,
            key=f"{prefix}:response",
        ),
    }

    hint_key = f"hints:{scenario.id}"
    hint_count = int(st.session_state.get(hint_key, 0))
    if hint_count:
        st.markdown("**Hints revealed**")
        for hint in scenario.hints[:hint_count]:
            st.info(hint)
    if hint_count < len(scenario.hints) and st.button("Reveal next hint", key=f"hint-button:{scenario.id}"):
        st.session_state[hint_key] = hint_count + 1
        st.rerun()
    return answers


def render_solution_and_rubric(
    bank: QuestionBank,
    scenario: Scenario,
    answers: dict[str, str],
    record: dict[str, object],
    store: ProgressStore,
) -> None:
    reveal_key = f"solution:{scenario.id}"
    if record.get("completed"):
        st.session_state[reveal_key] = True
    if not st.session_state.get(reveal_key):
        if st.button("Submit investigation and reveal model answer", use_container_width=True):
            st.session_state[reveal_key] = True
            st.rerun()
        return

    solution = scenario.solution
    st.divider()
    st.subheader("Model investigation")
    st.markdown("**Injected fault profile**")
    for fault in scenario.fault_profile:
        st.code(f"{fault.flag} = {fault.variant}", language=None)
    st.markdown("**Root cause**")
    st.write(solution["root_cause"])
    st.markdown("**Investigation path**")
    st.write(solution["investigation"])
    st.markdown("**Expected evidence**")
    for evidence in solution["expected_evidence"]:
        st.write(f"• {evidence}")
    st.markdown("**PromQL examples**")
    for query in solution["promql"]:
        st.code(query, language="promql")
    st.markdown("**Response and remediation**")
    st.write(solution["remediation"])
    st.info(solution["learning_notes"])

    st.subheader("Self-assessment rubric")
    saved_ids = set(record.get("checked_rubric_ids", []))
    checked: set[str] = set()
    for criterion in scenario.rubric:
        criterion_id = criterion["id"]
        selected = st.checkbox(
            f"{criterion['criterion']} ({criterion['points']} points)",
            value=criterion_id in saved_ids,
            key=f"rubric:{scenario.id}:{criterion_id}",
        )
        if selected:
            checked.add(criterion_id)
    score = score_rubric(scenario.rubric, checked)
    st.metric("Self-assessed score", f"{score}/100")
    if st.button("Save review and mark complete", type="primary", use_container_width=True):
        store.save_submission(bank.id, scenario.id, answers, checked, score)
        st.success("Progress saved locally.")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="E-Commerce SRE Learning Lab", page_icon="🛰️", layout="wide")
    st.title("E-Commerce SRE Learning Lab")
    st.write("Practice SRE thinking against the OpenTelemetry Astronomy Shop, from reliability contracts to live incident debugging.")

    config = LabConfig.from_environment(APP_DIR)
    manager = FlagManager(config)
    store = ProgressStore(config.state_dir / "progress.json")

    try:
        bank = load_selected_bank()
    except (BankValidationError, OSError) as exc:
        st.error(f"Question bank could not be loaded: {exc}")
        st.stop()

    st.sidebar.caption(bank.description)
    try:
        completed = store.completed_ids(bank.id)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    total = len(bank.scenarios)
    st.sidebar.progress(len(completed) / total, text=f"{len(completed)} of {total} completed")
    level_id, scenario = select_scenario(bank, completed)
    level = next(item for item in bank.levels if item.id == level_id)
    st.sidebar.info(level.objective)

    live_ok, live_message = flag_api_health(config.flag_api_url)
    if live_ok:
        st.sidebar.success(live_message)
    else:
        st.sidebar.warning(live_message)

    bank_compatible = False
    compatibility_error = ""
    try:
        _, local_flags = manager.read_source()
        validate_bank_against_flags(bank, local_flags)
        bank_compatible = True
    except (FlagManagerError, BankValidationError) as exc:
        compatibility_error = str(exc)
        st.sidebar.error(f"Flag validation: {compatibility_error}")

    st.sidebar.markdown("**Open lab tools**")
    st.sidebar.link_button("Storefront", config.shop_url, use_container_width=True)
    st.sidebar.link_button("Load generator", config.loadgen_url, use_container_width=True)
    st.sidebar.link_button("Grafana", config.grafana_url, use_container_width=True)
    st.sidebar.link_button("Jaeger", config.jaeger_url, use_container_width=True)

    with st.sidebar.expander("Local configuration"):
        st.code(
            "\n".join(
                [
                    f"Shop: {config.shop_url}",
                    f"Flag API: {config.flag_api_url}",
                    f"Flag file: {config.flag_file}",
                    f"State: {config.state_dir}",
                ]
            )
        )
    if st.sidebar.checkbox("Enable progress reset"):
        if st.sidebar.button("Reset this bank's progress", use_container_width=True):
            store.reset_bank(bank.id)
            st.rerun()

    st.caption(f"{level.title} · {', '.join(scenario.concepts)}")
    st.header(scenario.title)
    st.write(scenario.briefing)
    render_reliability_contract(scenario)
    render_lab_controls(bank, scenario, manager, live_ok, bank_compatible)

    record = store.scenario_record(bank.id, scenario.id)
    answers = render_investigation(scenario, record)
    render_solution_and_rubric(bank, scenario, answers, record, store)


if __name__ == "__main__":
    main()
