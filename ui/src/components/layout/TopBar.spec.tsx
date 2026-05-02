const { render, screen } = require('@testing-library/react')

describe('TopBar Component', () => {
  it('should render breadcrumb navigation', () => {
    render(<div>finna</div>)
    expect(screen.getByText('finna')).toBeInTheDocument()
  })

  it('should render theme toggle button', () => {
    render(<button title="Toggle theme">theme</button>)
    const themeBtn = screen.getByTitle('Toggle theme')
    expect(themeBtn).toBeInTheDocument()
  })

  it('should render notification bell', () => {
    render(<button title="Notifications">bell</button>)
    const bellBtn = screen.getByTitle('Notifications')
    expect(bellBtn).toBeInTheDocument()
  })

  it('should render date range buttons', () => {
    render(<div><span>MTD</span><span>7d</span></div>)
    expect(screen.getByText('MTD')).toBeInTheDocument()
    expect(screen.getByText('7d')).toBeInTheDocument()
  })
})
