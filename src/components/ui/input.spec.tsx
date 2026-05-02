import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { Input } from './input'

describe('Input Component', () => {
  it('should render input element', () => {
    render(<Input />)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('should render with placeholder', () => {
    render(<Input placeholder="Enter value" />)
    expect(screen.getByPlaceholderText('Enter value')).toBeInTheDocument()
  })

  it('should handle text input', async () => {
    const user = userEvent.setup()
    render(<Input />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'test value')
    expect(input).toHaveValue('test value')
  })

  it('should apply custom className', () => {
    render(<Input className="custom-input" />)
    expect(screen.getByRole('textbox')).toHaveClass('custom-input')
  })

  it('should render with type password', () => {
    render(<Input type="password" />)
    const input = document.querySelector('input')
    expect(input).toHaveAttribute('type', 'password')
  })

  it('should handle disabled state', () => {
    render(<Input disabled />)
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('disabled')
  })

  it('should pass additional props to input', () => {
    render(<Input id="test-input" name="test" />)
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('id', 'test-input')
    expect(input).toHaveAttribute('name', 'test')
  })
})
