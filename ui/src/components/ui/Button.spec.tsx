const { render, screen } = require('@testing-library/react')
const userEvent = require('@testing-library/user-event').default

describe('Button Component', () => {
  it('should render button with label', async () => {
    const user = userEvent.setup()
    render(<button data-slot="button">Click me</button>)
    const button = screen.getByText('Click me')
    expect(button).toBeInTheDocument()
    await user.click(button)
  })

  it('should be disabled when disabled prop is true', () => {
    render(<button disabled>Click me</button>)
    const button = screen.getByText('Click me')
    expect(button).toHaveAttribute('disabled')
  })

  it('should apply custom className', () => {
    render(<button className="custom-class">Click me</button>)
    const button = screen.getByText('Click me')
    expect(button).toHaveClass('custom-class')
  })
})
