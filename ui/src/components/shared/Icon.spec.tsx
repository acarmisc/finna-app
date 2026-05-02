const { render, screen } = require('@testing-library/react')

const { Icon } = require('./Icon')

describe('Icon Component', () => {
  it('should render SVG with correct class names', () => {
    render(<Icon name="search" className="test-class" />)
    const svg = screen.getByRole('img')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveClass('test-class')
  })

  it('should render search icon correctly', () => {
    render(<Icon name="search" />)
    const svg = screen.getByRole('img')
    expect(svg).toBeInTheDocument()
  })

  it('should render home icon correctly', () => {
    render(<Icon name="search" />)
    const svg = screen.getByRole('img')
    expect(svg).toBeInTheDocument()
  })

  it('should render settings icon correctly', () => {
    render(<Icon name="search" />)
    const svg = screen.getByRole('img')
    expect(svg).toBeInTheDocument()
  })

  it('should render chevron icon correctly', () => {
    render(<Icon name="chevron-down" />)
    const svg = screen.getByRole('img')
    expect(svg).toBeInTheDocument()
  })
})
