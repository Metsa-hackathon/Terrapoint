(function () {
  "use strict";

  const form = document.getElementById("question-form");
  const question = document.getElementById("question");
  const submitButton = document.getElementById("submit-button");
  const status = document.getElementById("request-status");
  const errorMessage = document.getElementById("error-message");
  const result = document.getElementById("result");
  const resultTitle = document.getElementById("result-title");
  const claimType = document.getElementById("claim-type");
  const confidence = document.getElementById("confidence");
  const answerSections = document.getElementById("answer-sections");
  const clarification = document.getElementById("clarification");
  const actions = document.getElementById("actions");
  const limitations = document.getElementById("limitations");
  const limitationsPanel = document.getElementById("limitations-panel");
  const sourceList = document.getElementById("source-list");
  const relatedPanel = document.getElementById("related-panel");
  const relatedList = document.getElementById("related-list");
  let activeRequest = null;

  const claimLabels = {
    statistical_estimate: "Statistiline hinnang",
    statistical_comparison: "Statistiline võrdlus",
    statistical_estimate_and_trend_caveat: "Statistiline hinnang ja trendipiirang",
    statistical_estimate_with_definition_warning: "Statistiline hinnang ja definitsioon",
    statistical_and_methodological_explanation: "Statistika ja metoodika",
    statistical_method_explanation: "Statistiline metoodika",
    methodological_explanation: "Metoodiline selgitus",
    source_scope_explanation: "Allikate ulatuse selgitus",
    trend_explanation_with_abstention: "Trend vajab aegrida",
    partial_statistical_answer_with_abstention: "Osaline statistiline vastus",
    evidence_based_risk_explanation: "Tõendipõhine riskiselgitus",
    factual_explanation: "Faktiselgitus",
    clarification_required: "Vajab täpsustust",
    clarification_and_data_requirement: "Vajab piirkonda ja näitajat",
    value_judgement: "Faktid ja väärtushinnang",
    fact_value_boundary: "Faktid ja väärtushinnang",
    legal_information_not_advice: "Õigusinfo, mitte õigusnõu",
    legal_information_with_required_redirect: "Õigusinfo ja ametlik suunamine",
    legal_and_ecological_definition: "Õiguslik ja ökoloogiline mõiste",
    service_direction: "Suunamine ametlikku teenusesse",
    no_supported_evidence: "Tõendit ei leitud"
  };

  const confidenceLabels = {
    high: "Tugev vaste",
    medium: "Keskmine vaste",
    low: "Nõrk vaste"
  };

  function clearNode(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function element(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function safeUrl(value) {
    try {
      const parsed = new URL(value, window.location.origin);
      if (parsed.origin === window.location.origin || parsed.protocol === "https:") return parsed.href;
    } catch (_error) {
      return null;
    }
    return null;
  }

  function sourceNumbers(sources) {
    const mapping = new Map();
    sources.forEach(function (source, index) {
      mapping.set(source.id, index + 1);
    });
    return mapping;
  }

  function renderAnswer(payload) {
    const sources = Array.isArray(payload.sources) ? payload.sources : [];
    const sourceMap = sourceNumbers(sources);
    const answer = payload.answer || { sections: [], limitations: [] };
    clearNode(answerSections);
    clearNode(clarification);
    clearNode(actions);
    clearNode(limitations);
    clearNode(sourceList);
    clearNode(relatedList);

    claimType.textContent = claimLabels[answer.claim_type] || "Allikapõhine selgitus";
    const confidenceValue = payload.retrieval && payload.retrieval.confidence;
    confidence.textContent = confidenceLabels[confidenceValue] || "";
    confidence.hidden = !confidence.textContent;

    (answer.sections || []).forEach(function (section) {
      const card = element("article", "answer-card " + (section.kind === "methodology" ? "methodology" : "answer"));
      card.appendChild(element("h3", "", section.title || "Selgitus"));
      card.appendChild(element("p", "", section.text || ""));
      const numbers = (section.citations || []).map(function (id) { return sourceMap.get(id); }).filter(Boolean);
      if (numbers.length) card.appendChild(element("p", "citation-note", "Viited: " + numbers.map(function (number) { return "[" + number + "]"; }).join(", ")));
      answerSections.appendChild(card);
    });

    if (payload.clarification) {
      clarification.appendChild(element("p", "clarification-card", payload.clarification));
    }

    (payload.actions || []).forEach(function (action) {
      const href = safeUrl(action.url);
      if (!href) return;
      const link = element("a", "action-link", action.label || "Ava teenus");
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      actions.appendChild(link);
    });

    (answer.limitations || []).forEach(function (text) {
      limitations.appendChild(element("li", "", text));
    });
    limitationsPanel.hidden = !limitations.children.length;

    sources.forEach(function (source) {
      const item = element("li", "source-card");
      const href = safeUrl(source.url);
      if (href) {
        const link = element("a", "", source.title || source.publisher || "Allikas");
        link.href = href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        item.appendChild(link);
      } else {
        item.appendChild(element("strong", "", source.title || "Allikas"));
      }
      const dateText = source.data_year ? "Andmeaasta " + source.data_year : (source.updated_at ? "Uuendatud " + source.updated_at : "Ajaseis allikas");
      item.appendChild(element("span", "source-meta", (source.publisher || "") + " · " + dateText));
      item.appendChild(element("span", "source-locator", source.locator || "Vaata viidatud lehte"));
      sourceList.appendChild(item);
    });

    (payload.related_questions || []).slice(0, 4).forEach(function (text) {
      const button = element("button", "question-chip", text);
      button.type = "button";
      button.addEventListener("click", function () { submitQuestion(text); });
      relatedList.appendChild(button);
    });
    relatedPanel.hidden = !relatedList.children.length;
    result.hidden = false;
    resultTitle.focus({ preventScroll: true });
    announceHeight();
  }

  async function submitQuestion(value) {
    const cleanQuestion = String(value === undefined ? question.value : value).trim();
    question.value = cleanQuestion;
    errorMessage.hidden = true;
    errorMessage.textContent = "";
    if (cleanQuestion.length < 3 || cleanQuestion.length > 500) {
      question.setAttribute("aria-invalid", "true");
      errorMessage.textContent = "Kirjuta 3–500 tähemärgi pikkune küsimus.";
      errorMessage.hidden = false;
      question.focus();
      announceHeight();
      return;
    }

    question.removeAttribute("aria-invalid");
    if (activeRequest) activeRequest.abort();
    activeRequest = new AbortController();
    submitButton.disabled = true;
    form.setAttribute("aria-busy", "true");
    status.textContent = "Otsin kinnitatud allikatest…";
    try {
      const response = await fetch("/api/forest-search", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: cleanQuestion, top_k: 3 }),
        signal: activeRequest.signal
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Teenuse päring ebaõnnestus.");
      renderAnswer(payload);
      status.textContent = payload.status === "answered" ? "Vastus leitud." : "Vaata täpsustust või sobivat ametlikku teenust.";
    } catch (error) {
      if (error.name === "AbortError") return;
      errorMessage.textContent = error.message || "Teenusega ei õnnestunud ühendust saada. Proovi uuesti.";
      errorMessage.hidden = false;
      status.textContent = "Vastust ei õnnestunud laadida.";
    } finally {
      submitButton.disabled = false;
      form.removeAttribute("aria-busy");
      activeRequest = null;
      announceHeight();
    }
  }

  function announceHeight() {
    window.requestAnimationFrame(function () {
      window.parent.postMessage({
        type: "terrapoint:forest-resize",
        height: Math.ceil(document.documentElement.scrollHeight)
      }, "*");
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    submitQuestion();
  });

  document.querySelectorAll("[data-question]").forEach(function (button) {
    button.addEventListener("click", function () { submitQuestion(button.dataset.question); });
  });

  if ("ResizeObserver" in window) {
    new ResizeObserver(announceHeight).observe(document.body);
  }
  window.addEventListener("load", announceHeight);
}());
