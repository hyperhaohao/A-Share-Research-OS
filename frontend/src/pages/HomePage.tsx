import { useState } from "react";
import { useTranslation } from "react-i18next";
import { InstrumentSearch } from "../components/InstrumentSearch";
import { ResearchPipelineCard } from "../components/ResearchPipelineCard";

export function HomePage() {
  const { t } = useTranslation();
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(null);

  return (
    <main className="page">
      <h1>{t("home.title")}</h1>
      <p className="secondary">{t("home.description")}</p>

      <InstrumentSearch onSelect={(iid) => setSelectedInstrument(iid)} />

      {selectedInstrument && (
        <ResearchPipelineCard instrumentId={selectedInstrument} />
      )}
      {!selectedInstrument && (
        <section className="card">
          <p className="secondary">{t("home.searchPrompt")}</p>
        </section>
      )}
    </main>
  );
}

