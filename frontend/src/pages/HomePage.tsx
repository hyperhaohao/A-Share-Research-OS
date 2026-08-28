import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { InstrumentSearch } from "../components/InstrumentSearch";
import { ResearchPipelineCard } from "../components/ResearchPipelineCard";

/**
 * Home (PW0): search → pick an instrument → live research pipeline.
 * Watchlist "立即研究" deep-links here with ?instrument=<id>&run=1, which
 * pre-selects the instrument and starts the run immediately.
 */
export function HomePage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const instrumentParam = searchParams.get("instrument");
  const autoRun = searchParams.get("run") === "1";
  const [selectedInstrument, setSelectedInstrument] = useState<string | null>(
    instrumentParam,
  );

  useEffect(() => {
    if (instrumentParam) setSelectedInstrument(instrumentParam);
  }, [instrumentParam]);

  return (
    <main className="page">
      <h1>{t("home.title")}</h1>
      <p className="secondary">{t("home.description")}</p>

      <InstrumentSearch onSelect={(iid) => setSelectedInstrument(iid)} />

      {selectedInstrument && (
        <ResearchPipelineCard
          key={selectedInstrument}
          instrumentId={selectedInstrument}
          autoStart={autoRun}
        />
      )}
      {!selectedInstrument && (
        <section className="card">
          <p className="secondary">{t("home.searchPrompt")}</p>
        </section>
      )}
    </main>
  );
}
