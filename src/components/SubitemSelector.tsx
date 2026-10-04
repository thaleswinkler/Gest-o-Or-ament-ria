import { useMemo, useState, useEffect, type ChangeEvent } from 'react';
import { BookOpen, Sparkles, CheckCircle2, Edit3, HelpCircle } from 'lucide-react';
import { montarOpcoesSubitem, obterFuncaoSubitem, obterNomeSubitem } from '../lib/subitens';

interface SubitemSelectorProps {
  nd: string;
  descricao: string;
  value: string;
  onChange: (subitem: string) => void;
  disabled?: boolean;
}

export function SubitemSelector({
  nd,
  descricao,
  value,
  onChange,
  disabled = false
}: SubitemSelectorProps) {
  const [modoManual, setModoManual] = useState(false);
  const [manualCode, setManualCode] = useState(value);

  // Calcula opções com base na ND e na Descrição
  const { opcoes, defaultCodigo } = useMemo(() => {
    return montarOpcoesSubitem(nd, descricao, value);
  }, [nd, descricao, value]);

  // Se não tiver valor selecionado, pré-seleciona o defaultCodigo inteligente
  useEffect(() => {
    if (!value && defaultCodigo && !modoManual) {
      onChange(defaultCodigo);
    }
  }, [defaultCodigo, value, modoManual, onChange]);

  const funcaoTexto = useMemo(() => {
    return obterFuncaoSubitem(nd, value);
  }, [nd, value]);

  const nomeSubitem = useMemo(() => {
    return obterNomeSubitem(nd, value);
  }, [nd, value]);

  const handleSelectChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === '__MANUAL__') {
      setModoManual(true);
    } else {
      setModoManual(false);
      onChange(val);
    }
  };

  const handleManualInput = (e: ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 2);
    setManualCode(digits);
    onChange(digits);
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          Sub Item da ND (Identificação por Função Oficial SIAFI)
        </label>
        {modoManual ? (
          <button
            type="button"
            onClick={() => setModoManual(false)}
            className="text-[11px] text-emerald-700 hover:text-emerald-800 underline flex items-center gap-1"
          >
            Voltar para lista inteligente
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setModoManual(true)}
            className="text-[11px] text-slate-500 hover:text-slate-800 flex items-center gap-1"
          >
            <Edit3 className="w-3 h-3" />
            Digitar código manualmente
          </button>
        )}
      </div>

      {modoManual ? (
        <div className="flex gap-2 items-center">
          <input
            type="text"
            maxLength={2}
            value={manualCode}
            onChange={handleManualInput}
            disabled={disabled}
            placeholder="Ex: 01"
            className="w-24 px-3 py-2 text-xs font-mono font-bold uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none bg-white text-center"
          />
          <span className="text-xs text-slate-500">
            {nomeSubitem ? `(${nomeSubitem})` : 'Digite o código de 2 dígitos'}
          </span>
        </div>
      ) : (
        <select
          value={value}
          onChange={handleSelectChange}
          disabled={disabled}
          className="w-full text-xs py-2 px-3 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-600 focus:outline-none text-slate-800 shadow-2xs font-medium"
        >
          {opcoes.map((op, idx) => (
            <option key={idx} value={op.codigo}>
              {op.label}
            </option>
          ))}
          <option value="__MANUAL__">✏️ Digitar outro código manualmente...</option>
        </select>
      )}

      {/* Caixa de Exibição da FUNÇÃO Oficial do SIAFI */}
      {funcaoTexto ? (
        <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/80 text-[11px] text-slate-600 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-slate-800">
            <BookOpen className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
            <span>
              Função Oficial do Subitem {value} {nomeSubitem && `(${nomeSubitem})`}:
            </span>
          </div>
          <p className="text-[11px] leading-relaxed text-slate-600 line-clamp-3 hover:line-clamp-none transition-all">
            {funcaoTexto}
          </p>
        </div>
      ) : value ? (
        <div className="p-2 bg-amber-50/60 rounded-lg border border-amber-200/60 text-[11px] text-amber-800 flex items-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <span>Subitem <strong>{value}</strong> selecionado (Código personalizado).</span>
        </div>
      ) : null}
    </div>
  );
}
