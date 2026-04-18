import React from 'react';

interface MiniBarsProps {
  data: number[];
}

export function MiniBars({ data }: MiniBarsProps) {
  const max = Math.max(...data);
  return (
    <div className="fn-minibars">
      {data.map((v, i) => (
        <div key={i} className="fn-minibar">
          <div style={{ height: (v / max * 100) + '%', background: 'var(--fg)' }} />
        </div>
      ))}
    </div>
  );
}
