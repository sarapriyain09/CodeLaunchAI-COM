export default function Contact() {
  return (
    <div className="flex flex-col items-center bg-gray-100 p-6">
      <header className="w-full bg-white shadow-md p-4">
        <h1 className="text-2xl font-bold text-center">Contact Us</h1>
      </header>
      <section className="mt-6 w-full max-w-4xl">
        <img
          src="https://picsum.photos/seed/hero-contact/1200/700"
          alt="A serene landscape representing communication"
          className="w-full h-60 object-cover rounded-lg"
        />
        <h2 className="mt-4 text-xl font-semibold text-center">Get in Touch</h2>
        <p className="mt-2 text-center text-gray-700">
          We would love to hear from you! Reach out to us for any inquiries or feedback.
        </p>
      </section>
      <section className="mt-8 w-full max-w-4xl grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow-md">
          <img
            src="https://picsum.photos/seed/card-contact-1/400/300"
            alt="Contact support"
            className="w-full h-32 object-cover rounded-lg"
          />
          <h3 className="mt-2 text-lg font-semibold">Customer Support</h3>
          <p className="text-gray-600">We're here to help you with any issues.</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-md">
          <img
            src="https://picsum.photos/seed/card-contact-2/400/300"
            alt="Sales inquiries"
            className="w-full h-32 object-cover rounded-lg"
          />
          <h3 className="mt-2 text-lg font-semibold">Sales Inquiries</h3>
          <p className="text-gray-600">Interested in our products? Let's talk!</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-md">
          <img
            src="https://picsum.photos/seed/card-contact-3/400/300"
            alt="General feedback"
            className="w-full h-32 object-cover rounded-lg"
          />
          <h3 className="mt-2 text-lg font-semibold">General Feedback</h3>
          <p className="text-gray-600">We value your thoughts and suggestions.</p>
        </div>
      </section>
      <section className="mt-8 w-full max-w-4xl text-center">
        <h2 className="text-xl font-semibold">Connect with Us on WhatsApp</h2>
        <p className="mt-2 text-gray-700">For immediate assistance, reach out via WhatsApp.</p>
        <a
          href="https://wa.me/1234567890"
          className="mt-4 inline-block bg-green-500 text-white py-2 px-4 rounded-lg hover:bg-green-600 transition"
        >
          Message Us
        </a>
      </section>
    </div>
  );
}
