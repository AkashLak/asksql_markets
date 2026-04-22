interface Props {
  explanation: string
  success: boolean
  error: string | null
}

function highlightNumbers(text: string): React.ReactNode[] {
  const parts = text.split(/(\$?[\d,]+(?:\.\d+)?(?:\s?[BMK%])?(?:\s?(?:billion|million|trillion))?)/g)
  return parts.map((part, i) => {
    const isNum = /^\$?[\d,]+/.test(part) && part.replace(/[,$.\s]/g, '').length >= 2
    return isNum
      ? <span key={i} style={{ color: 'rgba(255,255,255,0.95)', fontWeight: 600 }}>{part}</span>
      : part
  })
}

export function AnswerCard({ explanation, success, error }: Props) {
  if (error && !success) {
    return (
      <div style={{
        background: 'rgba(255,255,255,0.03)',
        border: '0.5px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        padding: '16px 20px',
      }}>
        <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.55)', lineHeight: 1.65 }}>{explanation}</p>
      </div>
    )
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)',
      border: '0.5px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      padding: '18px 20px',
    }}>
      <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.75)', lineHeight: 1.7 }}>
        {highlightNumbers(explanation)}
      </p>
    </div>
  )
}
